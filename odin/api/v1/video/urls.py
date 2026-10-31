from django.urls import path

from odin.api.v1.video.views import VideoRetrieveView, VideoStreamView, VideosView, VideoTrailerView


app_name = "video"


urlpatterns = [
    path("videos/", VideosView.as_view({"get": "list"}), name="videos"),
    path("videos/<int:pk>/", VideoRetrieveView.as_view({"get": "retrieve"}), name="video"),
    path("videos/<int:pk>/stream/", VideoStreamView.as_view(), name="stream"),
    path("videos/<int:pk>/trailer/", VideoTrailerView.as_view(), name="trailer"),
]
