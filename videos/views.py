from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView, ListAPIView
from videos.models import Video, VideoChunk, VideoFormat
from videos.serializers import (
    VideoCreateSerializer,
    VideoListSerializer,
    VideoDetailSerializer,
    VideoFormatSerializer,
    VideoChunkSerializer,
)

class VideoListCreateView(ListCreateAPIView):
    def get_queryset(self):
        user_id = self.request.user_id
        if self.request.method == 'GET':
            return Video.objects.by_user(user_id).ready().with_formats().recent()
        return Video.objects.by_user(user_id)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return VideoCreateSerializer
        return VideoListSerializer


class VideoDetailView(RetrieveUpdateDestroyAPIView):
    serializer_class = VideoDetailSerializer

    def get_queryset(self):
        return Video.objects.by_user(self.request.user_id).with_ready_formats().with_chunks()


class VideoFormatListView(ListAPIView):
    serializer_class = VideoFormatSerializer

    def get_queryset(self):
        video_id = self.kwargs['video_id']
        return VideoFormat.objects.filter(video_id=video_id).ready().with_video()


class VideoChunkListView(ListAPIView):
    serializer_class = VideoChunkSerializer

    def get_queryset(self):
        video_id = self.kwargs['video_id']
        return VideoChunk.objects.by_video(video_id).ordered()
