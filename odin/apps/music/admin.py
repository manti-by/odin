from django.contrib import admin

from odin.apps.music.models import Music


@admin.register(Music)
class MusicAdmin(admin.ModelAdmin):
    list_display = ("artist", "title", "album", "year")
    search_fields = ("artist", "album", "title")
    list_filter = ("artist", "album")
