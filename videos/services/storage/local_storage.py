import os
from videos.services.storage.base_storage import BaseStorage

class LocalStorage(BaseStorage):
    def upload(self, chunk: bytes, video_id: str, chunk_index: int) -> str:
        base_dir = "/tmp/videostream/chunks"
        dir_path = os.path.join(base_dir, str(video_id))
        os.makedirs(dir_path, exist_ok=True)
        
        file_path = os.path.join(dir_path, str(chunk_index))
        with open(file_path, "wb") as f:
            f.write(chunk)
            
        return file_path
