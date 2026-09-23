from django.urls import path

from odin.api.v1.logs.views import LogErrorsView, LogsView


app_name = "logs"


urlpatterns = [
    path("", LogsView.as_view(), name="create"),
    path("errors/", LogErrorsView.as_view(), name="errors"),
]
