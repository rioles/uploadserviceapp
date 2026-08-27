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
        logger.info("========== UPLOAD CHUNK START ==========")

        serializer = ChunkUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        logger.info("1. Serializer OK")

        validated_data = serializer.validated_data
        request.keycloak_user_id = request.user.id
        logger.info(f"2. User OK: {request.user.id}")
        chunk_dto = ChunkData.from_request(request)
        logger.info(
            f"3. DTO OK: video={chunk_dto.video_id}, "
            f"index={chunk_dto.chunk_index}, "
            f"hash={chunk_dto.sha256[:16]}..."
        )
        logger.info("4. Starting S3 upload...")
        try:
            chunk_file_bytes = validated_data['chunk'].read()
            logger.info(
                f"5. Chunk read OK: {len(chunk_file_bytes)} bytes"
            )
            s3_key = get_storage().upload(
                chunk=chunk_file_bytes,
                video_id=chunk_dto.video_id,
                chunk_index=chunk_dto.chunk_index
            )
            logger.info(f"6. S3 upload OK: {s3_key}")
        except Exception:
            logger.exception("❌ S3 UPLOAD FAILED")
            raise
        final_chunk_dto = chunk_dto.with_s3_key(s3_key)
        logger.info("7. Sending task to Celery...")
        try:
            result = persist_chunk.delay(final_chunk_dto.to_dict())
            logger.info(
                f"8. Celery task submitted successfully: {result.id}"
            )
        except Exception:
            logger.exception("❌ CELERY SUBMISSION FAILED")
            raise
        logger.info("========== UPLOAD CHUNK END ==========")
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
