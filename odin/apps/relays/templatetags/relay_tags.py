import calendar

from django import template
from django.utils.translation import gettext_lazy as _


register = template.Library()


@register.filter
def day_name(day):
    """Convert a day number 0-6, where 0 is Sunday (see strftime %w) to its localized name."""
    return _(calendar.day_name[int(day)])
