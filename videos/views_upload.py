# videos/views_upload.py
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, JSONParser
from rest_framework.permissions import IsAuthenticated

# Importation de l'authentification Keycloak depuis ton package core
from core.authentication import KeycloakAuthentication 

from videos.serializers_upload import ChunkUploadSerializer, FinalizeUploadSerializer
from videos.services.storage import get_storage
from videos.schemas import ChunkData, FinalizeData

# Importations corrigées selon tes noms exacts de fichiers de tâches
from videos.tasks.chunk_tasks import persist_chunk
from videos.tasks.finalize_tasks import finalize_video

logger = logging.getLogger(__name__)


class UploadChunkView(APIView):
    parser_classes = [MultiPartParser]
    # Injection de ton système Keycloak au niveau de la vue
    authentication_classes = [KeycloakAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        # 1. Validation de la forme de la requête
        serializer = ChunkUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # En Django, pour que le DTO puisse lire request.user.id de manière transparente :
        # On injecte la propriété attendue par notre méthode ChunkData.from_request
        request.keycloak_user_id = request.user.id

        # 2. Construction du DTO initial (génère l'UUID7 de chunk_id automatiquement)
        chunk_dto = ChunkData.from_request(request)

        # 3. Lecture et upload physique du Blob binaire vers S3
        chunk_file_bytes = validated_data['chunk'].read()
        s3_key = get_storage().upload(
            chunk=chunk_file_bytes,
            video_id=chunk_dto.video_id,
            chunk_index=chunk_dto.chunk_index
        )
        print("this is the key", s3_key)
        # 4. Envoi du DTO enrichi de sa clé S3 vers Celery au format dictionnaire
        final_chunk_dto = chunk_dto.with_s3_key(s3_key)
        persist_chunk.delay(final_chunk_dto.to_dict())

        return Response({'status': 'ok'}, status=200)


class FinalizeUploadView(APIView):
    parser_classes = [JSONParser]
    authentication_classes = [KeycloakAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = FinalizeUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.keycloak_user_id = request.user.id
        finalize_dto = FinalizeData.from_request(request)
        finalize_video.delay(finalize_dto.to_dict())

        return Response({'status': 'processing'}, status=202)
