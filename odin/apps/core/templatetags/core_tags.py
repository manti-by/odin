from decimal import Decimal

from django import template
from django.utils import formats


register = template.Library()


@register.filter(is_safe=False)
def format_decimal(value: Decimal) -> str:
    return str(formats.localize(round(value, 1), use_l10n=False))
