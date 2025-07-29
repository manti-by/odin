from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from odin.apps.music.models import Music


class ArtistListFilter(admin.SimpleListFilter):
    title = _("Artist")
    parameter_name = "artist"
    template = "admin/select_filter.html"

    def lookups(self, request, model_admin):
        return Music.objects.values_list("artist", "artist").distinct("artist")

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(artist__contains=self.value())
        return queryset


class AlbumListFilter(admin.SimpleListFilter):
    title = _("Album")
    parameter_name = "album"
    template = "admin/select_filter.html"

    def lookups(self, request, model_admin):
        queryset = Music.objects.all()
        if request.GET.get("artist"):
            queryset = queryset.filter(artist__contains=request.GET.get("artist"))
        return queryset.values_list("album", "album").distinct("album")

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(album__contains=self.value())
        return queryset


@admin.register(Music)
class MusicAdmin(admin.ModelAdmin):
    list_display = ("artist", "title", "album", "year")
    search_fields = ("artist", "album", "title")
    list_filter = (ArtistListFilter, AlbumListFilter)
