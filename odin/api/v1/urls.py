from django.urls import include, path

app_name = "v1"


urlpatterns = [
    path("core/", include("odin.api.v1.core.urls"), name="core"),
]
