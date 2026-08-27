import boto3
from django.conf import settings
from videos.services.storage.base_storage import BaseStorage

class S3Storage(BaseStorage):
    def __init__(self):
        # 1. Configuration de la région (fallback sécurisé)
        region = getattr(settings, 'AWS_DEFAULT_REGION', 'us-east-1')
        kwargs = {'region_name': region}

        # 2. Injection conditionnelle des clés (Dev local uniquement)
        # En Prod, Boto3 utilisera automatiquement Pod Identity / IRSA
        access_key = getattr(settings, 'AWS_ACCESS_KEY_ID', None)
        secret_key = getattr(settings, 'AWS_SECRET_ACCESS_KEY', None)

        if access_key and secret_key:
            kwargs['aws_access_key_id'] = access_key
            kwargs['aws_secret_access_key'] = secret_key

        # 3. Endpoint personnalisé (uniquement pour Dev local avec MinIO/LocalStack)
        endpoint_url = getattr(settings, 'AWS_S3_ENDPOINT_URL', None)
        if endpoint_url:
            kwargs['endpoint_url'] = endpoint_url

        self.s3_client = boto3.client('s3', **kwargs)
        self.bucket_name = settings.AWS_S3_BUCKET

    def upload(self, chunk: bytes, video_id: str, chunk_index: int) -> str:
        key = f"chunks/{video_id}/{chunk_index}"
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=chunk
        )
        return key
