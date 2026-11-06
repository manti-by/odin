from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from odin.apps.video.models import Video


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "title_en",
        "year",
        "imdb_rating",
        "metadata_status",
        "trailer_status",
        "is_available",
        "updated_at",
    )
    list_filter = ("is_available", "translation_status", "metadata_status", "trailer_status")
    search_fields = ("title", "title_en", "title_omdb", "filename", "path")
    readonly_fields = ("filename", "mtime", "size", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("path", "filename", "title", "title_en", "title_omdb", "year", "is_available")}),
        (_("Details"), {"fields": ("imdb_rating", "description", "genres")}),
        (
            _("Fetching"),
            {
                "fields": (
                    "trailer",
                    "translation_status",
                    "metadata_status",
                    "trailer_status",
                    "translation_attempts",
                    "metadata_attempts",
                    "trailer_attempts",
                )
            },
        ),
        (_("File"), {"fields": ("mtime", "size", "created_at", "updated_at")}),
    )
