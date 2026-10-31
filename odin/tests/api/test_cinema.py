from urllib.parse import quote

import pytest

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from odin.apps.cinema.models import FetchStatus, Video
from odin.tests.factories import VideoFactory


@pytest.mark.django_db
class TestCinemaVideosAPI:
    def setup_method(self):
        self.client = APIClient()
        self.url = reverse("api:v1:cinema:videos")

    def test_cinema__list_empty(self):
        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 0

    def test_cinema__list_only_available(self):
        VideoFactory(is_available=True)
        VideoFactory(is_available=False)

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 1

    def test_cinema__list_does_not_expose_the_library_path(self):
        VideoFactory(path="/mnt/data/Movies/Heat (1995).mkv", filename="Heat (1995).mkv")

        response = self.client.get(self.url, format="json")
        assert "path" not in response.data["results"][0]

    def test_cinema__response_fields(self):
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

    def test_cinema__pagination(self):
        for _ in range(20):
            VideoFactory()

        response = self.client.get(self.url, format="json")
        assert response.data["count"] == 20
        assert len(response.data["results"]) == 15


@pytest.mark.django_db
class TestCinemaVideoRetrieveAPI:
    def setup_method(self):
        self.client = APIClient()

    def test_cinema__retrieve(self):
        video = VideoFactory(title="Heat", year=1995)

        response = self.client.get(reverse("api:v1:cinema:video", args=[video.pk]), format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "Heat"

    def test_cinema__retrieve_non_existent(self):
        response = self.client.get(reverse("api:v1:cinema:video", args=[999]), format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cinema__retrieve_unavailable_video(self):
        video = VideoFactory(is_available=False)

        response = self.client.get(reverse("api:v1:cinema:video", args=[video.pk]), format="json")
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestCinemaStreamAPI:
    def setup_method(self):
        self.client = APIClient()

    def test_stream__returns_accel_redirect(self, tmp_path):
        path = tmp_path / "Heat (1995).mkv"
        path.write_bytes(b"video")
        video = VideoFactory(path=str(path), filename=path.name)

        response = self.client.get(reverse("api:v1:cinema:stream", args=[video.pk]))
        assert response.status_code == status.HTTP_200_OK
        assert response["X-Accel-Redirect"] == f"/cinema-media/{quote(str(path))}"
        assert response["Content-Type"] == "video/x-matroska"
        assert response["Accept-Ranges"] == "bytes"

    def test_stream__missing_file(self):
        video = VideoFactory(path="/mnt/data/Movies/missing.mkv")

        response = self.client.get(reverse("api:v1:cinema:stream", args=[video.pk]))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_stream__unavailable_video(self, tmp_path):
        path = tmp_path / "Heat (1995).mkv"
        path.write_bytes(b"video")
        video = VideoFactory(path=str(path), is_available=False)

        response = self.client.get(reverse("api:v1:cinema:stream", args=[video.pk]))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_stream__no_authentication_required(self, tmp_path):
        path = tmp_path / "Heat (1995).mkv"
        path.write_bytes(b"video")
        video = VideoFactory(path=str(path))

        response = APIClient().get(reverse("api:v1:cinema:stream", args=[video.pk]))
        assert response.status_code == status.HTTP_200_OK

    def test_trailer__returns_accel_redirect(self, tmp_path, settings):
        settings.CINEMA_TRAILERS_DIR = str(tmp_path)
        (tmp_path / "1-heat-1995.mp4").write_bytes(b"trailer")
        video = VideoFactory(trailer="1-heat-1995.mp4")

        response = self.client.get(reverse("api:v1:cinema:trailer", args=[video.pk]))
        assert response.status_code == status.HTTP_200_OK
        assert response["X-Accel-Redirect"] == "/cinema-trailers/1-heat-1995.mp4"
        assert response["Content-Type"] == "video/mp4"

    def test_trailer__no_trailer_linked(self):
        video = VideoFactory(trailer="")

        response = self.client.get(reverse("api:v1:cinema:trailer", args=[video.pk]))
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_trailer__file_missing(self, tmp_path, settings):
        settings.CINEMA_TRAILERS_DIR = str(tmp_path)
        video = VideoFactory(trailer="1-heat-1995.mp4")

        response = self.client.get(reverse("api:v1:cinema:trailer", args=[video.pk]))
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestCinemaModel:
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
