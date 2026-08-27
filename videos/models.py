import uuid6
from django.db import models
from videos.managers import VideoManager, VideoChunkManager, VideoFormatManager

class Video(models.Model):

    class Status(models.TextChoices):
        PENDING    = 'pending',    'Pending'
        PROCESSING = 'processing', 'Processing'
        READY      = 'ready',      'Ready'
        FAILED     = 'failed',     'Failed'
        QUEUED     = 'queued',     'Queued'

    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    upload_id = models.CharField(max_length=255, unique=True)
    user_id = models.CharField(max_length=255)
    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    total_chunks = models.IntegerField(default=0)
    size_bytes = models.BigIntegerField(blank=True, null=True)
    composite_hash = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    hls_master_s3_key = models.CharField(max_length=512, blank=True, null=True)
    duration_s = models.IntegerField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects = VideoManager()

    class Meta:
        db_table = 'videos'
        indexes = [
            models.Index(fields=['user_id'], name='idx_videos_user_id'),
            models.Index(fields=['composite_hash', 'status'], name='idx_videos_hash_status'),
        ]

    @property
    def ready_formats(self):
        return getattr(self, '_ready_formats', self.formats.filter(ready=True))

    @ready_formats.setter
    def ready_formats(self, value):
        self._ready_formats = value

    def __str__(self):
        return f"Video {self.id} - {self.title or 'No Title'}"


class Chunk(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    sha256 = models.CharField(max_length=64, unique=True)  # Index unique natif
    s3_key = models.CharField(max_length=512)  # CharField plus adapté pour un index s3_key
    size_bytes = models.BigIntegerField()  # BigIntegerField pour cohérence avec Video.size_bytes
    occurrence_count = models.IntegerField(default=1)

    class Meta:
        db_table = 'chunks'

    def __str__(self):
        return f"Chunk {self.id} (SHA: {self.sha256[:8]}) - Count: {self.occurrence_count}"


class VideoChunk(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    video = models.ForeignKey(
        Video,
        on_delete=models.CASCADE,
        db_column='video_id',
        related_name='chunks'
    )
    chunk = models.ForeignKey(
        Chunk,
        on_delete=models.PROTECT,
        db_column='chunk_id',
        related_name='video_assignments'
        # L'index individuel sur chunk_id est créé automatiquement par Django ici
    )
    chunk_index = models.IntegerField()
    objects = VideoChunkManager()

    class Meta:
        db_table = 'video_chunks'
        ordering = ['chunk_index']
        # Remplacement moderne et propre de unique_together
        constraints = [
            models.UniqueConstraint(fields=['video', 'chunk_index'], name='uidx_video_chunk_index')
        ]

    def __str__(self):
        return f"Video {self.video_id} [Chunk {self.chunk_index}] -> Chunk Phys. {self.chunk_id}"


class VideoFormat(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid6.uuid7, editable=False)
    video = models.ForeignKey(
        Video,
        on_delete=models.CASCADE,
        db_column='video_id',
        related_name='formats'
        # L'index individuel sur video_id est créé automatiquement par Django ici
    )
    resolution = models.CharField(max_length=20)  # ex: "1080p", "720p"
    width = models.PositiveIntegerField(blank=True, null=True)
    height = models.PositiveIntegerField(blank=True, null=True)
    s3_key = models.CharField(max_length=512)
    codec = models.CharField(max_length=20, default='h264')
    bitrate_kbps = models.IntegerField(blank=True, null=True)
    ready = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    objects = VideoFormatManager()

    class Meta:
        db_table = 'video_formats'
        indexes = [
            models.Index(fields=['s3_key'], name='idx_formats_s3_key'),
        ]

    def __str__(self):
        return f"VideoFormat {self.id} - Video {self.video_id} [{self.resolution}]"
