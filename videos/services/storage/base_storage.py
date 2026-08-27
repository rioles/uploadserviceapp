from abc import ABC, abstractmethod

class BaseStorage(ABC):

    @abstractmethod
    def upload(self, chunk: bytes, video_id: str, chunk_index: int) -> str:
        """
        Upload a chunk and return the storage key.
        - Local: returns the absolute file path
        - S3: returns the S3 key (e.g. chunks/{video_id}/{chunk_index})
        """
        pass
