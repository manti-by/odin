from django.contrib import admin

from .models import Log


@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    list_display = ("levelname", "filename", "name", "msg", "asctime")
    search_fields = ("msg",)
    list_filter = ("levelname", "filename", "asctime")
