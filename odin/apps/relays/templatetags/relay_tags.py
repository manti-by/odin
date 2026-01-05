import calendar

from django import template
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _


register = template.Library()


@register.filter
def day_name(day):
    """Convert a day number 0-6, where 0 is Sunday (see strftime %w) to its localized name."""
    return _(calendar.day_name[int(day)])


@register.simple_tag
def relay_state_image(state):  # noqa: S308
    """Return heating.svg or cooling.svg image based on relay state."""
    if state == "OFF":
        return mark_safe('<img src="/static/img/cooling.svg" alt="cooling" width="24">')  # noqa: S308
    return mark_safe('<img src="/static/img/heating.svg" alt="heating" width="24">')  # noqa: S308
