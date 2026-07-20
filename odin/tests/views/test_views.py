import pytest

from rest_framework import status


@pytest.mark.django_db
@pytest.mark.views
class TestViews:
    def test_spa_deep_link_returns_error_when_build_missing(self, client):
        response = client.get("/sensors/home/", follow=True)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert b"Frontend build not available" in response.content

    def test_spa_deep_link_boiler_returns_error_when_build_missing(self, client):
        response = client.get("/sensors/boiler/", follow=True)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert b"Frontend build not available" in response.content

    def test_random_spa_route_returns_error_when_build_missing(self, client):
        response = client.get("/some/deep/link/", follow=True)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert b"Frontend build not available" in response.content

    def test_admin_route_still_works(self, client):
        response = client.get("/admin/", follow=True)
        assert response.status_code == status.HTTP_200_OK
