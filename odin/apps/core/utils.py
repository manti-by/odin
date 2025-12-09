import math
from decimal import Decimal

from django.template.loader import render_to_string

from odin.api.v1.core.serializers import MetricChoices


GREEN_COLOR = "#87C540"
YELLOW_COLOR = "#FFDD00"
RED_COLOR = "#DA525D"

LIGHT_GREY_COLOR = "#E9E9E9"
DARK_GREY_COLOR = "#404040"


def create_metric_gauge_chart(value: Decimal, metric: MetricChoices) -> str:
    min_value, max_value, min_green_value, max_green_value = 6, 35, 18, 27
    if metric == MetricChoices.HUMIDITY:
        min_value, max_value, min_green_value, max_green_value = 0, 100, 35, 65
    if metric == MetricChoices.PRESSURE:
        min_value, max_value, min_green_value, max_green_value = 631, 825, 740, 780

    value_color = GREEN_COLOR
    if value < min_green_value:
        value_color = YELLOW_COLOR if metric == MetricChoices.PRESSURE else RED_COLOR
    if value > max_green_value:
        value_color = RED_COLOR if metric == MetricChoices.PRESSURE else YELLOW_COLOR

    return create_gauge_chart(
        value=value,
        min_value=min_value,
        max_value=max_value,
        min_green_value=min_green_value,
        max_green_value=max_green_value,
        value_color=value_color,
    )


def create_gauge_chart(
    value: Decimal,
    min_value: int = 0,
    max_value: int = 100,
    min_green_value: int = 35,
    max_green_value: int = 65,
    size: int = 70,
    stroke_width: int = 4,
    fill_color: str = GREEN_COLOR,
    value_color: str = GREEN_COLOR,
    text_color: str = LIGHT_GREY_COLOR,
    background_color: str = DARK_GREY_COLOR,
    center_x: int | None = None,
    center_y: int | None = None,
    start_angle: Decimal = -200,
    end_angle: Decimal = 20,
) -> str:
    """
    Create a circular gauge chart as SVG string.

    Args:
        value: Current value to display on the gauge
        min_value: Minimum value for the gauge range
        max_value: Maximum value for the gauge range
        min_green_value: Minimum value for the gauge green range
        max_green_value: Maximum value for the gauge green range
        size: Size of the SVG (width and height in pixels)
        stroke_width: Width of the gauge arc stroke
        fill_color: Color of the filled arc
        value_color: Color of the value point
        text_color: Color of the text
        background_color: Color of the background arc
        center_x: X coordinate of center (defaults to size/2)
        center_y: Y coordinate of center (defaults to size/2)
        start_angle: Starting angle in degrees (default -135 for bottom-left)
        end_angle: Ending angle in degrees (default 135 for bottom-right)

    Returns:
        SVG string representation of the gauge chart
    """
    # Calculate center if not provided
    if center_x is None:
        center_x = size // 2
    if center_y is None:
        center_y = size // 2

    # Calculate radius
    radius = (size - stroke_width) // 2 - 10

    # Normalize value to 0-1 range
    normalized_value = max(0, min(1, (value - min_value) / (max_value - min_value)))

    # Convert angles to radians
    start_rad = math.radians(start_angle)
    end_rad = math.radians(end_angle)

    # Calculate the angle for the current value
    value_angle = start_angle + (end_angle - start_angle) * normalized_value
    value_rad = math.radians(value_angle)

    # Calculate shifted borders
    left_border = max(0, min(1, (min_green_value - min_value) / (max_value - min_value)))
    left_border_angle = start_angle + (end_angle - start_angle) * left_border
    left_border_rad = math.radians(left_border_angle)

    right_border = max(0, min(1, (max_green_value - min_value) / (max_value - min_value)))
    right_border_angle = start_angle + (end_angle - start_angle) * right_border
    right_border_rad = math.radians(right_border_angle)

    # Helper function to calculate point on circle
    def point_on_circle(angle_rad, r):
        x = center_x + r * math.cos(angle_rad)
        y = center_y + r * math.sin(angle_rad)
        return x, y

    # Calculate arc endpoints
    start_x, start_y = point_on_circle(start_rad, radius)
    end_x, end_y = point_on_circle(end_rad, radius)

    left_x, left_y = point_on_circle(left_border_rad, radius)
    right_x, right_y = point_on_circle(right_border_rad, radius)

    value_x, value_y = point_on_circle(value_rad, radius)

    # Generate path elements for an SQV image
    start_arc = f"M {start_x} {start_y} A {radius} {radius} 0 0 1 {left_x} {left_y}"
    filled_arc = f"M {left_x} {left_y} A {radius} {radius} 0 0 1 {right_x} {right_y}"
    end_arc = f"M {right_x} {right_y} A {radius} {radius} 0 0 1 {end_x} {end_y}"

    # Render using Django template engine
    return render_to_string(
        "chart.svg",
        {
            "size": size,
            "view_box": f"0 0 {size} {size - 15}",
            "value": round(value, 0),
            "start_arc": start_arc,
            "end_arc": end_arc,
            "value_x": value_x,
            "value_y": value_y,
            "center_x": center_x,
            "center_y": center_y + size // 20,
            "filled_arc": filled_arc,
            "fill_color": fill_color,
            "text_color": text_color,
            "target_value_color": value_color,
            "background_color": background_color,
            "stroke_width": stroke_width,
        },
    )
