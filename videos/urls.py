from django.urls import path
from videos.views import (
    VideoListCreateView,
    VideoDetailView,
    VideoFormatListView,
    VideoChunkListView,
)
from videos.views_upload import UploadChunkView, FinalizeUploadView

urlpatterns = [
    # vidéos
    path('videos/',                          VideoListCreateView.as_view()),
    path('videos/<uuid:pk>/',                VideoDetailView.as_view()),
    path('videos/<uuid:video_id>/formats/',  VideoFormatListView.as_view()),
    path('videos/<uuid:video_id>/chunks/',   VideoChunkListView.as_view()),

    # upload
    path('upload/chunk/',    UploadChunkView.as_view(),    name='upload-chunk'),
    path('upload/finalize/', FinalizeUploadView.as_view(), name='upload-finalize'),
]
