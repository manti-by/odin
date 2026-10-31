from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _


class FetchStatus(models.TextChoices):
    PENDING = "PENDING", _("Pending")
    FETCHED = "FETCHED", _("Fetched")
    NOT_FOUND = "NOT_FOUND", _("Not found")
    ERROR = "ERROR", _("Error")


class VideoQuerySet(models.QuerySet):
    def available(self) -> VideoQuerySet:
        return self.filter(is_available=True)

    def pending_metadata(self) -> VideoQuerySet:
        return self.available().filter(metadata_status__in=(FetchStatus.PENDING, FetchStatus.ERROR))

    def pending_trailers(self) -> VideoQuerySet:
        return self.available().filter(trailer_status__in=(FetchStatus.PENDING, FetchStatus.ERROR))


class VideoManager(models.Manager):
    def get_queryset(self) -> VideoQuerySet:
        return VideoQuerySet(self.model, using=self._db)

    def available(self) -> VideoQuerySet:
        return self.get_queryset().available()

    def pending_metadata(self) -> VideoQuerySet:
        return self.get_queryset().pending_metadata()

    def pending_trailers(self) -> VideoQuerySet:
        return self.get_queryset().pending_trailers()


class Video(models.Model):
    """One video file on the media share plus its cached OMDb metadata and trailer."""

    path: models.CharField[str] = models.CharField(max_length=1024, unique=True, verbose_name=_("Path"))
    filename: models.CharField[str] = models.CharField(max_length=255, verbose_name=_("File name"))
    title: models.CharField[str] = models.CharField(max_length=255, verbose_name=_("Title"))
    year: models.PositiveIntegerField[int] | None = models.PositiveIntegerField(
        null=True, blank=True, verbose_name=_("Year")
    )
    imdb_rating: models.DecimalField[Decimal] | None = models.DecimalField(
        max_digits=3, decimal_places=1, null=True, blank=True, verbose_name=_("IMDb rating")
    )
    description: models.TextField[str] = models.TextField(blank=True, default="", verbose_name=_("Description"))
    genres: models.JSONField[list[str]] = models.JSONField(default=list, verbose_name=_("Genres"))
    trailer: models.CharField[str] = models.CharField(
        max_length=255, blank=True, default="", verbose_name=_("Trailer file")
    )

    metadata_status: models.CharField[str] = models.CharField(
        max_length=16,
        choices=FetchStatus.choices,
        default=FetchStatus.PENDING,
        verbose_name=_("Metadata status"),
    )
    trailer_status: models.CharField[str] = models.CharField(
        max_length=16,
        choices=FetchStatus.choices,
        default=FetchStatus.PENDING,
        verbose_name=_("Trailer status"),
    )
    metadata_attempts: models.PositiveIntegerField[int] = models.PositiveIntegerField(
        default=0, verbose_name=_("Metadata attempts")
    )
    trailer_attempts: models.PositiveIntegerField[int] = models.PositiveIntegerField(
        default=0, verbose_name=_("Trailer attempts")
    )

    mtime: models.FloatField[float] = models.FloatField(default=0, verbose_name=_("Modified at"))
    size: models.BigIntegerField[int] = models.BigIntegerField(default=0, verbose_name=_("Size"))
    is_available: models.BooleanField[bool] = models.BooleanField(default=True, verbose_name=_("Is available"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created at"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated at"))

    objects = VideoManager()

    class Meta:
        ordering = ("title",)
        verbose_name = _("video")
        verbose_name_plural = _("videos")

    def __str__(self) -> str:
        return self.release_label

    @property
    def has_trailer(self) -> bool:
        return bool(self.trailer)

    @property
    def release_label(self) -> str:
        return f"{self.title} ({self.year})" if self.year else self.title
