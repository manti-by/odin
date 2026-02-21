from django import template
from django.utils import formats


register = template.Library()


@register.filter
def currency_rate(value):
    if value is None:
        return "--"
    return formats.localize(value, use_l10n=False)


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
