from urllib.parse import quote

import pytest

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from odin.apps.video.models import FetchStatus, Video
from odin.tests.factories import VideoFactory


@pytest.mark.django_db
class TestVideosAPI:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:video:videos")

    def test_video__list_empty(self):
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0

    def test_video__list_only_available(self):
        VideoFactory(is_available=True)
        VideoFactory(is_available=False)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

    def test_video__list_does_not_expose_the_library_path(self):
        VideoFactory(path="/mnt/data/Movies/Heat (1995).mkv", filename="Heat (1995).mkv")

        response = self.client.get(self.url, format="json")
        assert "path" not in response.data["results"][0]

    def test_video__response_fields(self):
        video = VideoFactory(
            title="Heat",
            year=1995,
            imdb_rating="8.3",
            description="A crew of thieves.",
            genres=["Crime", "Drama"],
            trailer="1-heat-1995.mp4",
        )

        response = self.client.get(self.url, format="json")
        item = response.data["results"][0]
        assert item == {
            "id": video.pk,
            "title": "Heat",
            "filename": video.filename,
            "year": 1995,
            "imdb_rating": "8.3",
            "description": "A crew of thieves.",
            "genres": ["Crime", "Drama"],
            "trailer_available": True,
            "metadata_status": FetchStatus.PENDING,
            "trailer_status": FetchStatus.PENDING,
            "is_available": True,
            "created_at": item["created_at"],
        }

    def test_video__pagination(self):
        for _ in range(20):
            VideoFactory()

        response = self.client.get(self.url, format="json")
        assert response.data["count"] == 20
        assert len(response.data["results"]) == 15


@pytest.mark.django_db
class TestVideoRetrieveAPI:
    def setup_method(self):
        self.client = APIClient()

    def test_video__retrieve(self):
        video = VideoFactory(title="Heat", year=1995)

        response = self.client.get(reverse("api:v1:video:video", args=[video.pk]), format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "Heat"

    def test_video__retrieve_non_existent(self):
        response = self.client.get(reverse("api:v1:video:video", args=[999]), format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_video__retrieve_unavailable_video(self):
        video = VideoFactory(is_available=False)

        response = self.client.get(reverse("api:v1:video:video", args=[video.pk]), format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestVideoStreamAPI:
    def setup_method(self):
        self.client = APIClient()

    def test_stream__returns_accel_redirect(self, tmp_path, settings):
        settings.VIDEO_MEDIA_DIRS = (str(tmp_path),)
        path = tmp_path / "Heat (1995).mkv"
        path.write_bytes(b"video")
        video = VideoFactory(path=str(path), filename=path.name)

        response = self.client.get(reverse("api:v1:video:stream", args=[video.pk]))
        assert response.status_code == status.HTTP_200_OK
        assert response["X-Accel-Redirect"] == f"/video-media/{quote(str(path))}"
        assert response["Content-Type"] == "video/x-matroska"
        assert response["Accept-Ranges"] == "bytes"

    def test_stream__missing_file(self):
        video = VideoFactory(path="/mnt/data/Movies/missing.mkv")

        response = self.client.get(reverse("api:v1:video:stream", args=[video.pk]))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_stream__file_outside_media_dirs(self, tmp_path, settings):
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        outside = tmp_path / "private" / "secret.mkv"
        outside.parent.mkdir()
        outside.write_bytes(b"secret")
        settings.VIDEO_MEDIA_DIRS = (str(media_dir),)
        video = VideoFactory(path=str(outside), filename=outside.name)

        response = self.client.get(reverse("api:v1:video:stream", args=[video.pk]))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_stream__symlink_escape_is_rejected(self, tmp_path, settings):
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        outside = tmp_path / "secret.mkv"
        outside.write_bytes(b"secret")
        link = media_dir / "Heat (1995).mkv"
        link.symlink_to(outside)
        settings.VIDEO_MEDIA_DIRS = (str(media_dir),)
        video = VideoFactory(path=str(link.resolve()), filename=link.name)

        response = self.client.get(reverse("api:v1:video:stream", args=[video.pk]))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_stream__unavailable_video(self, tmp_path, settings):
        settings.VIDEO_MEDIA_DIRS = (str(tmp_path),)
        path = tmp_path / "Heat (1995).mkv"
        path.write_bytes(b"video")
        video = VideoFactory(path=str(path), is_available=False)

        response = self.client.get(reverse("api:v1:video:stream", args=[video.pk]))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_stream__no_authentication_required(self, tmp_path, settings):
        settings.VIDEO_MEDIA_DIRS = (str(tmp_path),)
        path = tmp_path / "Heat (1995).mkv"
        path.write_bytes(b"video")
        video = VideoFactory(path=str(path))

        response = APIClient().get(reverse("api:v1:video:stream", args=[video.pk]))
        assert response.status_code == status.HTTP_200_OK

    def test_trailer__returns_accel_redirect(self, tmp_path, settings):
        settings.VIDEO_TRAILERS_DIR = str(tmp_path)
        trailer = tmp_path / "1-heat-1995.mp4"
        trailer.write_bytes(b"trailer")
        video = VideoFactory(trailer=trailer.name)

        response = self.client.get(reverse("api:v1:video:trailer", args=[video.pk]))
        assert response.status_code == status.HTTP_200_OK
        assert response["X-Accel-Redirect"] == f"/video-trailers/{trailer.name}"
        assert response["Content-Type"] == "video/mp4"

    def test_trailer__outside_trailers_dir(self, tmp_path, settings):
        settings.VIDEO_TRAILERS_DIR = str(tmp_path / "trailers")
        outside = tmp_path / "secret.mp4"
        outside.write_bytes(b"secret")
        video = VideoFactory(trailer="../secret.mp4")

        response = self.client.get(reverse("api:v1:video:trailer", args=[video.pk]))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_trailer__no_trailer_linked(self):
        video = VideoFactory(trailer="")

        response = self.client.get(reverse("api:v1:video:trailer", args=[video.pk]))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_trailer__file_missing(self, tmp_path, settings):
        settings.VIDEO_TRAILERS_DIR = str(tmp_path)
        video = VideoFactory(trailer="1-heat-1995.mp4")

        response = self.client.get(reverse("api:v1:video:trailer", args=[video.pk]))
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestVideoModel:
    def test_video__release_label_with_year(self):
        video = Video(title="Heat", year=1995)
        assert video.release_label == "Heat (1995)"

    def test_video__release_label_without_year(self):
        video = Video(title="Heat", year=None)
        assert video.release_label == "Heat"

    def test_video__has_trailer(self):
        assert Video(trailer="1-heat.mp4").has_trailer is True
        assert Video(trailer="").has_trailer is False

    def test_video__pending_metadata_includes_retryable_errors(self):
        VideoFactory(metadata_status=FetchStatus.PENDING)
        VideoFactory(metadata_status=FetchStatus.ERROR)
        VideoFactory(metadata_status=FetchStatus.FETCHED)
        VideoFactory(metadata_status=FetchStatus.PENDING, is_available=False)

        assert Video.objects.pending_metadata().count() == 2
