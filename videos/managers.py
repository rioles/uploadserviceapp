# videos/managers.py
from django.db import models


# ─────────────────────────────────────────────────────────
# Video QuerySet & Manager
# ─────────────────────────────────────────────────────────

class VideoQuerySet(models.QuerySet):

    def ready(self):
        """
        Vidéos au statut final après upload complet.
        Équivaut à Video.Status.READY — string littéral utilisé ici pour
        éviter l'import circulaire (managers.py est importé par models.py).
        """
        return self.filter(status='ready')

    def processing(self):
        """Vidéos dont l'upload est encore en cours."""
        return self.filter(status='processing')

    def failed(self):
        """Vidéos dont l'upload a échoué."""
        return self.filter(status='failed')

    def by_user(self, user_id):
        return self.filter(user_id=user_id)

    def recent(self):
        return self.order_by('-created_at')

    def with_formats(self):
        return self.prefetch_related('formats')

    def with_chunks(self):
        """Jointure optimisée pour récupérer les liaisons de chunks."""
        return self.prefetch_related('chunks')

    def with_ready_formats(self):
        """Prefetch personnalisé mappé sur l'attribut dynamique ready_formats."""
        from django.apps import apps
        from django.db.models import Prefetch
        
        # Résolution sécurisée du modèle pour éviter TOUT risque d'import circulaire
        VideoFormat = apps.get_model('videos', 'VideoFormat')
        
        return self.prefetch_related(
            Prefetch(
                'formats',
                queryset=VideoFormat.objects.ready(),
                to_attr='ready_formats'
            )
        )

    def lightweight(self):
        """Limite les colonnes chargées en mémoire pour les listes simples."""
        return self.only('id', 'upload_id', 'title', 'status', 'user_id', 'created_at')


# Génération automatique du Manager à partir du QuerySet
VideoManager = models.Manager.from_queryset(VideoQuerySet)


# ─────────────────────────────────────────────────────────
# VideoFormat QuerySet & Manager
# ─────────────────────────────────────────────────────────

class VideoFormatQuerySet(models.QuerySet):

    def ready(self):
        return self.filter(ready=True)

    def by_resolution(self, resolution):
        return self.filter(resolution=resolution)

    def with_video(self):
        """Évite le problème de requêtes N+1 lors de l'accès à video."""
        return self.select_related('video')


VideoFormatManager = models.Manager.from_queryset(VideoFormatQuerySet)


# ─────────────────────────────────────────────────────────
# VideoChunk QuerySet & Manager
# ─────────────────────────────────────────────────────────

class VideoChunkQuerySet(models.QuerySet):

    def ordered(self):
        return self.order_by('chunk_index')

    def by_video(self, video_id):
        return self.filter(video_id=video_id)

    def with_relations(self):
        """
        Pré-charge la vidéo et le chunk physique associé en une seule requête SQL.
        Crucial pour les boucles de lecture ou de traitement lourd.
        """
        return self.select_related('video', 'chunk')

    def manifest_fields(self):
        """
        Prépare l'extraction des données minimales pour le manifeste.
        Reste chaînable car renvoie un QuerySet (de dictionnaires).
        """
        return self.values('chunk_index', 'chunk__s3_key', 'chunk__size_bytes')


class VideoChunkManager(models.Manager.from_queryset(VideoChunkQuerySet)):
    """
    Manager personnalisé pour VideoChunk.
    Contient les méthodes "terminales" qui exécutent la requête et retournent des données brutes.
    """
    
    def get_manifest_data(self, video_id):
        """
        OPTIMISATION MAJEURE : Récupère uniquement l'ordre des s3_key pour l'assemblage.
        Évite d'instancier des centaines d'objets Django complets en RAM.
        """
        return (
            self.get_queryset()
            .by_video(video_id)
            .ordered()
            .manifest_fields()
        )
