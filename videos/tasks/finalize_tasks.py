# videos/tasks/finalizer.py
import logging
import boto3

from celery import shared_task
from django.conf import settings
from django.db import transaction
import hashlib

from videos.schemas import ChunkOrder, FinalizeData

logger = logging.getLogger(__name__)

from functools import partial
from typing import Optional

from django.conf import settings
from django.db import transaction
from celery import shared_task

from videos.models import Video
import json

logger = logging.getLogger(__name__)

_dynamo_table = None

def get_dynamo_table():
    global _dynamo_table
    if _dynamo_table is None:
        # Configuration dynamique de la région (fallback sur us-east-1 si non définie)
        region = getattr(settings, 'AWS_DEFAULT_REGION', 'us-east-1')
        kwargs = {'region_name': region}

        # On n'injecte les clés statiques QUE si elles existent explicitement (ex: dev local)
        # En prod (EKS/Pod Identity/VPC Endpoint), Boto3 utilisera le rôle IAM automatiquement
        access_key = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
        secret_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)

        if access_key and secret_key:
            kwargs['aws_access_key_id'] = access_key
            kwargs['aws_secret_access_key'] = secret_key

        dynamodb = boto3.resource('dynamodb', **kwargs)
        _dynamo_table = dynamodb.Table(settings.DYNAMODB_CHUNK_TABLE)

    return _dynamo_table



def _process_existing_chunks(video_id: str, existing: list[ChunkOrder]) -> None:
    """
    Traite les chunks existants pour associer leurs références physiques à la nouvelle vidéo.
    - Élimine les risques de Deadlocks applicatifs grâce au tri séquentiel des hashes.
    - Protège l'idempotence des compteurs d'occurrences via l'analyse des VideoChunk préexistants.
    - Applique les changements en lot (bulk) pour optimiser les performances de la base de données.
    """
    if not existing:
        return

    from videos.models import Chunk, VideoChunk

    hashes = [c.hash for c in existing]
    hashes_sorted = sorted(list(set(hashes)))

    chunks = Chunk.objects.select_for_update().filter(sha256__in=hashes_sorted)
    chunks_dict = {c.sha256: c for c in chunks}

    existing_vc = set(
        VideoChunk.objects.filter(video_id=video_id, chunk__sha256__in=hashes_sorted)
        .values_list('chunk__sha256', flat=True)
    )

    video_chunks_to_create = []
    chunks_to_update = set()

    for c in existing:
        chunk = chunks_dict.get(c.hash)
        if not chunk:
            raise ValueError(f"Chunk physique manquant en base pour le hash: {c.hash}")

        video_chunks_to_create.append(
            VideoChunk(video_id=video_id, chunk_index=c.index, chunk=chunk)
        )
        
        if c.hash not in existing_vc:
            chunk.occurrence_count += 1
            chunks_to_update.add(chunk)

    if chunks_to_update:
        Chunk.objects.bulk_update(list(chunks_to_update), ['occurrence_count'])

    if video_chunks_to_create:
        VideoChunk.objects.bulk_create(video_chunks_to_create, ignore_conflicts=True)


def _build_dynamo_items(new_chunks: list[ChunkOrder]) -> list[dict]:
    """
    Construit la liste des enregistrements destinés à l'index DynamoDB.
    Vérifie la présence préalable en base SQL et lève une exception en cas de désynchronisation.
    """
    if not new_chunks:
        return []

    from videos.models import Chunk

    hashes = [c.hash for c in new_chunks]
    chunks_in_db = Chunk.objects.filter(sha256__in=hashes)
    chunks_by_hash = {c.sha256: c.s3_key for c in chunks_in_db}

    items = []
    for c in new_chunks:
        s3_key = chunks_by_hash.get(c.hash)
        if not s3_key:
            raise ValueError(f"Le chunk {c.hash} n'est pas encore synchronisé en base SQL.")
        
        items.append({
            'chunk_hash': c.hash,
            's3_url': s3_key, 
        })
    return items


def _store_dynamo_batch(items: list[dict]) -> None:
    """
    Envoie en lot les métadonnées des nouveaux chunks vers la table DynamoDB.
    L'opération est ignorée en environnement de développement local.
    """
    if not items:
        return
    table = get_dynamo_table()
    with table.batch_writer() as writer:
        for item in items:
            writer.put_item(Item=item)
    logger.info(f"[DYNAMO SUCCESS] {len(items)} items écrits dans DynamoDB.")


def _verify_integrity(video_id: str, total_chunks: int) -> None:
    """
    Valide l'intégrité de la structure de la vidéo.
    Vérifie que le nombre total de segments enregistrés correspond exactement aux attentes.
    """
    from videos.models import VideoChunk
    registered = VideoChunk.objects.filter(video_id=video_id).count()
    if registered != total_chunks:
        raise ValueError(f"Intégrité corrompue : {registered}/{total_chunks} chunks trouvés en DB.")
        
_sqs_client = None

def get_sqs_client():
    global _sqs_client
    if _sqs_client is None:
        # Configuration de la région (fallback sécurisé us-east-1)
        region = getattr(settings, 'AWS_DEFAULT_REGION', 'us-east-1')
        kwargs = {'region_name': region}

        # Injection conditionnelle des clés (Dev local uniquement)
        access_key = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
        secret_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)

        if access_key and secret_key:
            kwargs['aws_access_key_id'] = access_key
            kwargs['aws_secret_access_key'] = secret_key

        # Si un endpoint SQS personnalisé est configuré (ex: LocalStack ou Private DNS désactivé)
        endpoint_url = getattr(settings, 'AWS_SQS_ENDPOINT_URL', None)
        if endpoint_url:
            kwargs['endpoint_url'] = endpoint_url

        _sqs_client = boto3.client('sqs', **kwargs)

    return _sqs_client
    



def _send_transcode_message(
    video_id: str,
    complete_chunks: list[dict],
    is_deduplicated: bool = False,
    composite_hash: Optional[str] = None
) -> None:
    """
    Envoie un message SQS vers le worker transcoder (Java/MediaConvert).
    
    - Si is_deduplicated=True : complete_chunks est vide, composite_hash est transmis 
      pour permettre la duplication des VideoFormats par le worker.
    - Si is_deduplicated=False : complete_chunks contient la liste ordonnée des chunks
      pour effectuer le transcodage HLS multi-résolution.
    """
    message_body = {
        'video_id': video_id,
        'composite_hash': composite_hash,
        'is_deduplicated': is_deduplicated,
        'chunks': complete_chunks,  # Liste vide [] si dédupliqué, sinon liste ordonnée
        'target_resolutions': ['1080p', '720p', '480p', '360p'],
    }

    sqs = get_sqs_client()
    response = sqs.send_message(
        QueueUrl=settings.TRANSCODE_QUEUE_URL,
        MessageBody=json.dumps(message_body)
    )
    
    logger.info(
        f"[SQS SUCCESS] Message de transcodage envoyé pour la vidéo {video_id} "
        f"(Deduplicated: {is_deduplicated}, MessageId: {response['MessageId']})."
    )



@shared_task(bind=True, max_retries=5)
def finalize_video(self, finalize_dict: dict):
    """
    Tâche Celery d'orchestration de la finalisation d'upload.
    - Statut initial : PROCESSING (contrôle d'intégrité + calcul du hash).
    - Passage en QUEUED et envoi du message SQS (Java gère les VideoFormats et le status READY).
    """
    try:
        data = dict(finalize_dict)
        chunks_order = [ChunkOrder(**c) for c in data.pop('chunks_order')]
        finalize_data = FinalizeData(**data, chunks_order=chunks_order)

        existing_chunks = [c for c in chunks_order if c.s3_url is not None]
        new_chunks = [c for c in chunks_order if c.s3_url is None]

        with transaction.atomic():
            # 1. Enregistrement initial -> Statut PROCESSING
            video, created = Video.objects.update_or_create(
                id=finalize_data.upload_id,
                defaults={
                    'upload_id': finalize_data.upload_id,
                    'user_id': finalize_data.user_id,
                    'title': finalize_data.nom,
                    'description': finalize_data.description,
                    'total_chunks': finalize_data.total_chunks,
                    'size_bytes': finalize_data.file_size,
                    'status': Video.Status.PROCESSING,
                }
            )

            # 2. Association des chunks préexistants & Vérification d'intégrité
            if existing_chunks:
                _process_existing_chunks(finalize_data.upload_id, existing_chunks)

            _verify_integrity(finalize_data.upload_id, finalize_data.total_chunks)

            # 3. Assemblage de la liste complète et calcul du composite_hash
            complete_chunks = _build_complete_chunks_list(chunks_order)
            composite_hash = compute_video_composite_hash_from_dicts(complete_chunks)
            video.composite_hash = composite_hash

            # 4. Vérification de déduplication (Vidéo modèle déjà READY)
            existing_video = Video.objects.filter(
                composite_hash=composite_hash,
                status=Video.Status.READY
            ).exclude(id=video.id).first()

            if existing_video:
                # ✅ DÉDUPLICATION : Transmission de composite_hash + chunks=[]
                logger.info(
                    f"Vidéo {video.id} : dédupliquée depuis la vidéo {existing_video.id}. "
                    "Mis en file SQS avec is_deduplicated=True."
                )

                video.hls_master_s3_key = existing_video.hls_master_s3_key
                video.duration_s = existing_video.duration_s
                video.status = Video.Status.QUEUED
                video.save(update_fields=['composite_hash', 'hls_master_s3_key', 'duration_s', 'status'])

                transaction.on_commit(
                    partial(
                        _send_transcode_message,
                        video_id=finalize_data.upload_id,
                        complete_chunks=[],
                        is_deduplicated=True,
                        composite_hash=composite_hash
                    )
                )

            else:
                # ❌ NOUVEAU CONTENU : Transcodage complet requis par Java
                logger.info(
                    f"Vidéo {video.id} : nouveau hash {composite_hash[:8]}, "
                    "mis en file SQS pour transcodage."
                )

                video.status = Video.Status.QUEUED
                video.save(update_fields=['composite_hash', 'status'])

                transaction.on_commit(
                    partial(
                        _send_transcode_message,
                        video_id=finalize_data.upload_id,
                        complete_chunks=complete_chunks,
                        is_deduplicated=False,
                        composite_hash=composite_hash
                    )
                )

            # 5. Indexation DynamoDB pour les nouveaux chunks (Post-commit SQL)
            if new_chunks:
                dynamo_items = _build_dynamo_items(new_chunks)
                transaction.on_commit(
                    partial(_store_dynamo_batch, dynamo_items)
                )

        logger.info(f"[FINALIZE SUCCESS] Vidéo {finalize_data.upload_id} mise en file SQS avec succès.")

    except ValueError as exc:
        logger.warning(f"[FINALIZE RETRY] Dépendances non prêtes pour {finalize_dict.get('upload_id')}: {exc}")
        raise self.retry(exc=exc, countdown=3)

    except Exception as exc:
        if self.request.retries >= self.max_retries:
            logger.error(f"[FINALIZE FAILED] Échec définitif pour {finalize_dict.get('upload_id')}: {exc}")
            Video.objects.filter(id=finalize_dict.get('upload_id')).update(status=Video.Status.FAILED)

        logger.error(f"[FINALIZE ERROR] Erreur inattendue pour {finalize_dict.get('upload_id')}: {exc}")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)



def _build_complete_chunks_list(chunks_order: list[ChunkOrder]) -> list[dict]:
    """
    Construit la liste complète des chunks avec s3_url pour tous.
    - Chunks existants → s3_url déjà présent dans chunks_order
    - Nouveaux chunks  → s3_key récupéré depuis PostgreSQL
    """
    from videos.models import Chunk

    # 1. Identifier les chunks sans s3_url
    missing_s3 = [c.hash for c in chunks_order if not c.s3_url]

    # 2. Récupérer les s3_keys depuis PostgreSQL pour les nouveaux chunks
    s3_keys_by_hash = {}
    if missing_s3:
        chunks_in_db = Chunk.objects.filter(sha256__in=missing_s3).values('sha256', 's3_key')
        s3_keys_by_hash = {c['sha256']: c['s3_key'] for c in chunks_in_db}

    # 3. Construire la liste complète
    complete_list = []
    for c in chunks_order:
        s3_url = c.s3_url or s3_keys_by_hash.get(c.hash)

        if not s3_url:
            raise ValueError(f"s3_url manquant pour le chunk {c.hash} — désynchronisation DB.")

        complete_list.append({
            'chunk_index': c.index,
            'chunk_hash':  c.hash,
            's3_url':      s3_url,
        })

    # 4. Trier par index pour garantir l'ordre
    complete_list.sort(key=lambda x: x['chunk_index'])
    return complete_list
    
    
def compute_video_composite_hash_from_dicts(complete_chunks: list[dict]) -> str:
    """
    Calcule le hash composite à partir de la liste pré-triée par 'chunk_index'
    issue de _build_complete_chunks_list.
    """
    hasher = hashlib.sha256()
    
    # La liste est déjà triée par index à l'étape 4 de _build_complete_chunks_list
    for chunk in complete_chunks:
        hasher.update(chunk['chunk_hash'].encode('utf-8'))
        hasher.update(b'|')  # Séparateur de sécurité
        
    return hasher.hexdigest()
