from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from odin.apps.cinema.models import Video


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ("title", "year", "imdb_rating", "metadata_status", "trailer_status", "is_available", "updated_at")
    list_filter = ("is_available", "metadata_status", "trailer_status")
    search_fields = ("title", "filename", "path")
    readonly_fields = ("filename", "mtime", "size", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("path", "filename", "title", "year", "is_available")}),
        (_("Details"), {"fields": ("imdb_rating", "description", "genres")}),
        (
            _("Fetching"),
            {"fields": ("trailer", "metadata_status", "trailer_status", "metadata_attempts", "trailer_attempts")},
        ),
        (_("File"), {"fields": ("mtime", "size", "created_at", "updated_at")}),
    )
