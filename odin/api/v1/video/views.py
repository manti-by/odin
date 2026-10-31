from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import mixins
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from odin.api.v1.video.serializers import VideoSerializer
from odin.apps.video.models import Video
from odin.apps.video.services import get_trailer_stream, get_video_stream


class VideoBaseView(GenericViewSet):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    queryset = Video.objects.available()
    serializer_class = VideoSerializer


class VideosView(mixins.ListModelMixin, VideoBaseView):
    pass


class VideoRetrieveView(mixins.RetrieveModelMixin, VideoBaseView):
    pass


class VideoStreamView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    def get(self, request: Request, pk: int, *args: list, **kwargs: dict) -> HttpResponse:
        video = get_object_or_404(Video.objects.available(), pk=pk)
        return get_video_stream(video)


class VideoTrailerView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    def get(self, request: Request, pk: int, *args: list, **kwargs: dict) -> HttpResponse:
        video = get_object_or_404(Video.objects.available(), pk=pk)
        return get_trailer_stream(video)
