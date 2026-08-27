# videos/schemas.py
import uuid6
from dataclasses import dataclass


@dataclass
class ChunkData:
    """
    DTO — représente un chunk reçu de l'endpoint /upload/chunk.

    Mapping frontend → backend :
        uploadId   → video_id
        chunkIndex → chunk_index
        chunkHash  → sha256
        sizeBytes  → size_bytes
        JWT sub    → user_id (extrait du token Keycloak injecté dans request)
    """
    chunk_id:    str
    video_id:    str
    user_id:     str
    chunk_index: int
    sha256:      str
    s3_key:      str
    size_bytes:  int

    @classmethod
    def from_request(cls, request) -> 'ChunkData':
        """
        Construit le DTO à partir de la requête Django.
        L'user_id provient de l'extraction sécurisée du token Keycloak 
        effectuée en amont par le middleware/décorateur.
        """
        return cls(
            chunk_id=str(uuid6.uuid7()),
            video_id=request.data['uploadId'],
            user_id=getattr(request, 'keycloak_user_id', ''),  # Récupération sécurisée
            chunk_index=int(request.data['chunkIndex']),
            sha256=request.data['chunkHash'],
            s3_key='',  # Sera valorisé par le service d'upload S3
            size_bytes=int(request.data['sizeBytes']),
        )

    def with_s3_key(self, s3_key: str) -> 'ChunkData':
        """
        Retourne une nouvelle instance immuable enrichie de sa clé de stockage S3.
        """
        return ChunkData(
            chunk_id=self.chunk_id,
            video_id=self.video_id,
            user_id=self.user_id,
            chunk_index=self.chunk_index,
            sha256=self.sha256,
            s3_key=s3_key,
            size_bytes=self.size_bytes,
        )

    def to_dict(self) -> dict:
        return self.__dict__


@dataclass
class ChunkOrder:
    """
    Représente un chunk dans chunksOrder du payload /upload/finalize.
    Gère le mapping CamelCase du frontend (s3Url) vers snake_case.
    """
    index:      int
    hash:       str
    s3_url:     str | None
    size_bytes: int

    @classmethod
    def from_dict(cls, d: dict) -> 'ChunkOrder':
        return cls(
            index=d['index'],
            hash=d['hash'],
            s3_url=d.get('s3Url'),  # Reçoit 's3Url' depuis le JSON Next.js
            size_bytes=d['size_bytes'],
        )

    def to_dict(self) -> dict:
        return self.__dict__


@dataclass
class FinalizeData:
    """
    DTO — représente le payload complet de /upload/finalize.
    Gère l'alignement des clés CamelCase issues du client JavaScript.
    """
    upload_id:    str
    user_id:      str
    nom:          str
    domaine:      str
    description:  str
    file_name:    str
    file_size:    int
    file_type:    str
    total_chunks: int
    chunks_order: list[ChunkOrder]

    @classmethod
    def from_request(cls, request) -> 'FinalizeData':
        """
        Construit le DTO de finalisation en convertissant le format frontend.
        """
        body     = request.data
        metadata = body['metadata']
        return cls(
            upload_id=body['uploadId'],
            user_id=getattr(request, 'keycloak_user_id', ''),  # Extraction sécurisée du JWT
            nom=metadata['nom'],
            domaine=metadata['domaine'],
            description=metadata['description'],
            # Alignement avec le CamelCase du frontend Next.js :
            file_name=metadata['fileName'],
            file_size=metadata['fileSize'],
            file_type=metadata['fileType'],
            total_chunks=metadata['totalChunks'],
            chunks_order=[
                ChunkOrder.from_dict(c) for c in body['chunksOrder']
            ],
        )

    def to_dict(self) -> dict:
        return {
            **self.__dict__,
            'chunks_order': [c.to_dict() for c in self.chunks_order],
        }
