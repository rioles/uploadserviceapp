from videos.models import VideoChunk
from videos.services.storage import get_storage

class ChunkUploadService:
    @staticmethod
    def upload_chunk(video_id: str, chunk_index: int, chunk_hash: str, chunk_data: bytes, size_bytes: int) -> str:
        # 1. Execute get_storage().upload(...) to retrieve storage_key
        storage_key = get_storage().upload(chunk_data, video_id, chunk_index)
        
        # 2. Persist or update the entry in PostgreSQL using VideoChunk.objects.update_or_create()
        # Optimization: Use video_id=video_id directly in lookups/defaults to avoid extra SELECT
        VideoChunk.objects.update_or_create(
            video_id=video_id,
            chunk_index=chunk_index,
            defaults={
                's3_key': storage_key,
                'sha256': chunk_hash,
                'size_bytes': size_bytes,
            }
        )
        
        # 3. Return the storage_key
        return storage_key
