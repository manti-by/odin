from django import template
from django.utils.translation import gettext_lazy as _


register = template.Library()


@register.filter
def wind_direction_abbr(degrees):
    """Convert a wind direction in degrees to a `name`."""
    if degrees is None:
        return ""

    # Normalize degrees to 0-360 range
    degrees = float(degrees) % 360

    # Convert to 8-point compass (each direction is 45 degrees)
    # N=0, NE=45, E=90, SE=135, S=180, SW=225, W=270, NW=315
    # Add 22.5 to center each direction
    directions = [
        _("North"),
        _("North-East"),
        _("East"),
        _("South-East"),
        _("South"),
        _("South-West"),
        _("West"),
        _("North-West"),
    ]
    index = int((degrees + 22.5) / 45) % 8
    return directions[index]
