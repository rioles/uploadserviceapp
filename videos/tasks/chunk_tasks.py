# videos/tasks/chunk_task.py
import logging
import redis

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.db.models import F

from videos.schemas import ChunkData

logger = logging.getLogger(__name__)
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

# ─────────────────────────────────────────────────────────
# Cuckoo Filter Service
# ─────────────────────────────────────────────────────────
import logging
import redis
from django.conf import settings

logger = logging.getLogger(__name__)

class BloomFilterService:
    def __init__(
        self,
        key: str = 'bloom:chunks',
        capacity: int = 1_000_000,
        error_rate: float = 0.01  # Taux de faux positifs cible (1%)
    ):
        self.key        = key
        self.capacity   = capacity
        self.error_rate = error_rate
        
        # Initialisation automatique avec l'URL sécurisée (gère le TLS AWS et local)
        self.client     = redis.Redis.from_url(settings.REDIS_URL)

    def init_filter(self) -> None:
        """
        Réserve le Bloom Filter dans Redis — idempotent.
        À appeler dans AppConfig.ready().
        """
        try:
            # BF.RESERVE key error_rate capacity
            self.client.execute_command(
                'BF.RESERVE', self.key, self.error_rate, self.capacity
            )
            logger.info(
                f"[BLOOM] Filtre '{self.key}' initialisé "
                f"(capacité: {self.capacity}, taux d'erreur: {self.error_rate})."
            )
        except redis.exceptions.ResponseError as e:
            # Gère le cas où le filtre existe déjà de manière idempotente
            if "item already exists" in str(e).lower():
                pass  
            else:
                raise

    def add(self, chunk_hash: str) -> bool:
        """
        BF.ADD — Ajoute l'élément.
        Renvoie True si l'élément a bien été ajouté (nouveau), 
        False s'il était déjà potentiellement présent.
        """
        return bool(
            self.client.execute_command('BF.ADD', self.key, chunk_hash)
        )

    def exists(self, chunk_hash: str) -> bool:
        """
        BF.EXISTS — O(k). 
        Renvoie True s'il est potentiellement présent, False s'il ne l'est absolument pas.
        """
        return bool(
            self.client.execute_command('BF.EXISTS', self.key, chunk_hash)
        )


_cuckoo_service: BloomFilterService | None = None


def get_cuckoo_service() -> BloomFilterService:
    """Singleton — une seule connexion Redis par worker Celery."""
    global _cuckoo_service
    if _cuckoo_service is None:
        _cuckoo_service = BloomFilterService()
    return _cuckoo_service


# ─────────────────────────────────────────────────────────
# Helpers de Persistance (Exécutés dans la transaction)
# ─────────────────────────────────────────────────────────

def _ensure_video_stub(video_id: str, user_id: str) -> None:
    """
    Crée un Video minimal si absent.
    Requis par la contrainte FK de VideoChunk.
    """
    from videos.models import Video
    Video.objects.get_or_create(
        id=video_id,
        defaults={
            'upload_id':    video_id,
            'user_id':      user_id,
            'total_chunks': 0,
            'status':       Video.Status.PROCESSING,
        }
    )


def _persist_chunk_and_link(chunk_data: ChunkData) -> None:
    """
    Crée ou récupère le Chunk physique ET crée le VideoChunk.
    Gère l'incrémentation atomique du compteur d'occurrences.
    """
    from videos.models import Chunk, VideoChunk

    # 1. Récupère ou crée le chunk global (déduplication par SHA256)
    chunk, chunk_created = Chunk.objects.get_or_create(
        sha256=chunk_data.sha256,
        defaults={
            'id':               chunk_data.chunk_id,
            's3_key':           chunk_data.s3_key,
            'size_bytes':       chunk_data.size_bytes,
            'occurrence_count': 1,
        }
    )
    
    # 2. Associe ce chunk à la vidéo actuelle à un index précis
    _, vc_created = VideoChunk.objects.get_or_create(
        video_id=    chunk_data.video_id,
        chunk_index= chunk_data.chunk_index,
        defaults={'chunk': chunk}
    )

    # 3. Si le chunk existait déjà mais que le lien avec cette vidéo est NEUF,
    #    on incrémente le nombre d'utilisations de ce bloc physique.
    if not chunk_created and vc_created:
        Chunk.objects.filter(sha256=chunk_data.sha256).update(
            occurrence_count=F('occurrence_count') + 1
        )


def _update_cuckoo_filter(chunk_hash: str) -> None:
    """
    Ajoute le hash dans le Filtre de Bloom et logue le résultat.
    Appelé uniquement APRÈS le commit de la transaction PostgreSQL.
    """
    try:
        cuckoo  = get_cuckoo_service()
        is_new  = cuckoo.add(chunk_hash)
        
        if is_new:
            logger.info(f"✅ [REDIS BLOOM SUCCESS] Chunk hash inséré (NOUVEAU) : {chunk_hash[:16]}... dans la clé '{cuckoo.key}'")
        else:
            logger.warning(f"⚠️ [REDIS BLOOM DUPLICATE] Chunk hash DÉJÀ PRÉSENT (Doublon) : {chunk_hash[:16]}...")
            
    except Exception as e:
        logger.error(f"❌ [REDIS BLOOM ERROR] Impossible d'écrire le hash {chunk_hash[:16]}... dans Redis : {e}", exc_info=True)
        
def _update_cuckoo_filter(chunk_hash: str) -> None:
    """
    Ajoute le hash dans le Filtre de Bloom et logue le résultat.
    Appelé uniquement APRÈS le commit de la transaction PostgreSQL.
    """
    with tracer.start_as_current_span("redis.cuckoo_filter.add") as span:
        span.set_attribute("chunk.sha256", chunk_hash)
        try:
            cuckoo = get_cuckoo_service()
            is_new = cuckoo.add(chunk_hash)
            span.set_attribute("cuckoo.is_new", is_new)
            span.set_attribute("cuckoo.key", cuckoo.key)

            if is_new:
                logger.info(f"✅ [REDIS BLOOM SUCCESS] Chunk hash inséré (NOUVEAU) : {chunk_hash[:16]}... dans la clé '{cuckoo.key}'")
            else:
                logger.warning(f"⚠️ [REDIS BLOOM DUPLICATE] Chunk hash DÉJÀ PRÉSENT (Doublon) : {chunk_hash[:16]}...")

        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            logger.error(f"❌ [REDIS BLOOM ERROR] Impossible d'écrire le hash {chunk_hash[:16]}... dans Redis : {e}", exc_info=True)

# ─────────────────────────────────────────────────────────
# Celery Task
# ─────────────────────────────────────────────────────────

        

@shared_task(bind=True, max_retries=3)
def persist_chunk(self, chunk_dict: dict):
    """
    Traite un chunk uploadé.
    Garantit l'idempotence et élimine les Race Conditions DB/Cache via transaction.atomic.
    """
    try:
        chunk_data = ChunkData(**chunk_dict)

        with tracer.start_as_current_span("chunk.persist") as span:
            span.set_attribute("video.id", chunk_data.video_id)
            span.set_attribute("chunk.index", chunk_data.chunk_index)
            span.set_attribute("chunk.size_bytes", chunk_data.size_bytes)

            # On ouvre un bloc atomique global pour l'écriture SQL
            with transaction.atomic():
                _ensure_video_stub(chunk_data.video_id, chunk_data.user_id)
                _persist_chunk_and_link(chunk_data)

                # CORRECTION DE LA RACE CONDITION / ROLLBACK FANTÔME :
                # On demande à Django d'attendre que Postgres ait validé (COMMIT) l'écriture
                # avant d'envoyer l'information à Redis.
                transaction.on_commit(
                    lambda: _update_cuckoo_filter(chunk_data.sha256)
                )
    except Exception as exc:
        span = trace.get_current_span()
        span.set_attribute("task.retry_count", self.request.retries)
        logger.warning(f"[TASK RETRY] Erreur lors de la persistance du chunk: {exc}. Nouvelle tentative...")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)



