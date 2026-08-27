from videos.models import VideoChunk

class ChunkHashService:
    @staticmethod
    def update_s3_key(video_id: str, chunk_hash: str, s3_key: str) -> None:
        # Use .update() for efficiency (no object load)
        VideoChunk.objects.filter(
            video_id=video_id,
            sha256=chunk_hash
        ).update(
            s3_key=s3_key
        )
