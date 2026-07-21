import pytest

from rest_framework import status


@pytest.mark.django_db
@pytest.mark.views
class TestViews:
    @pytest.fixture(autouse=True)
    def _isolate_dist(self, tmp_path, settings):
        settings.FRONTEND_DIST_DIR = tmp_path

    @pytest.mark.parametrize("url", ("/sensors/home/", "/sensors/boiler/", "/some/deep/link/"))
    def test_spa_deep_link__returns_error_when_build_missing(self, client, url):
        response = client.get(url, follow=True)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert b"Frontend build not available" in response.content

    def test_admin_route__still_works(self, client):
        response = client.get("/admin/", follow=True)
        assert response.status_code == status.HTTP_200_OK
