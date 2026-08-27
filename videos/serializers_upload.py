# videos/serializers_upload.py
from rest_framework import serializers

class ChunkUploadSerializer(serializers.Serializer):
    uploadId   = serializers.CharField()
    chunkIndex = serializers.IntegerField()
    chunkHash  = serializers.CharField()
    sizeBytes  = serializers.IntegerField()
    chunk      = serializers.FileField()


class ChunkOrderItemSerializer(serializers.Serializer):
    """
    Représente un morceau dans le tableau chunksOrder transmis au /finalize.
    """
    index      = serializers.IntegerField()
    hash       = serializers.CharField()
    s3Url      = serializers.CharField(allow_null=True, required=False)
    size_bytes = serializers.IntegerField()  # Aligné sur ton DTO ChunkOrder backend


class UploadMetadataSerializer(serializers.Serializer):
    """
    Métadonnées descriptives de la vidéo envoyées lors de la finalisation.
    """
    nom         = serializers.CharField()
    domaine     = serializers.CharField()
    description = serializers.CharField(allow_blank=True, required=False)
    fileName    = serializers.CharField()
    fileSize    = serializers.IntegerField()
    fileType    = serializers.CharField()
    totalChunks = serializers.IntegerField()


class FinalizeUploadSerializer(serializers.Serializer):
    """
    Payload complet envoyé par le frontend Next.js lors de la finalisation.
    """
    uploadId    = serializers.CharField()
    metadata    = UploadMetadataSerializer()
    chunksOrder = ChunkOrderItemSerializer(many=True)
