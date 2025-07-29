from django.db import models
from django.db.models import JSONField, query
from django.utils.translation import gettext_lazy as _


class MusicQuerySet(query.QuerySet):
    pass


class MusicManager(models.Manager):
    pass


class Music(models.Model):
    file = models.FileField(max_length=256)
    meta = JSONField(default=dict)

    album = models.CharField(db_index=True, null=True, blank=True)
    artist = models.CharField(db_index=True, null=True, blank=True)
    title = models.CharField(null=True, blank=True)
    genre = models.CharField(null=True, blank=True)
    year = models.IntegerField(null=True, blank=True)
    has_cover = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = MusicManager.from_queryset(MusicQuerySet)()

    class Meta:
        verbose_name = _("music")
        verbose_name_plural = _("music")

    def __str__(self):
        return f"{self.artist} - {self.title}"
