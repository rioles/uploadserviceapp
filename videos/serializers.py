from rest_framework import serializers
from videos.models import Video, VideoChunk, VideoFormat


class VideoChunkSerializer(serializers.ModelSerializer):
    s3_key     = serializers.ReadOnlyField(source='chunk.s3_key')
    sha256     = serializers.ReadOnlyField(source='chunk.sha256')
    size_bytes = serializers.ReadOnlyField(source='chunk.size_bytes')

    class Meta:
        model = VideoChunk
        fields = ['id', 'chunk_index', 's3_key', 'sha256', 'size_bytes']
        read_only_fields = fields


class VideoFormatSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoFormat
        # AJOUT DE width ET height
        fields = ['id', 'resolution', 'width', 'height', 's3_key', 'codec', 'bitrate_kbps', 'ready']
        read_only_fields = fields


class VideoListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        # AJOUT DE duration_s ET composite_hash (pratique pour l'admin/analytics)
        fields = ['id', 'upload_id', 'title', 'status', 'size_bytes', 'duration_s', 'composite_hash', 'created_at']


class VideoDetailSerializer(serializers.ModelSerializer):
    formats  = VideoFormatSerializer(source='ready_formats', many=True, read_only=True)
    chunks   = VideoChunkSerializer(many=True, read_only=True)
    is_ready = serializers.SerializerMethodField()
    owner_id = serializers.CharField(source='user_id', read_only=True)

    class Meta:
        model = Video
        fields = [
            'id', 'upload_id', 'owner_id', 'title', 'description',
            'total_chunks', 'size_bytes', 'composite_hash', 'hls_master_s3_key',
            'duration_s', 'status', 'is_ready', 'formats', 'chunks', 'created_at'
        ]

    def get_is_ready(self, obj) -> bool:
        return obj.status == Video.Status.READY


class VideoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Video
        # AJOUT DE composite_hash POUR LA DÉDUPLICATION
        fields = ['upload_id', 'title', 'description', 'total_chunks', 'size_bytes', 'composite_hash']

    def validate_total_chunks(self, value):
        if value <= 0:
            raise serializers.ValidationError("total_chunks must be strictly greater than 0.")
        return value

    def create(self, validated_data):
        request = self.context['request']
        validated_data['user_id'] = str(request.user.id)
        return super().create(validated_data)
