import math
from decimal import Decimal


def create_gauge_chart(
    value: Decimal,
    min_value: Decimal = 0,
    max_value: Decimal = 100,
    threshold: Decimal = 10,
    size: int = 70,
    stroke_width: int = 4,
    background_color: str = "#404040",
    fill_color: str = "#4dcb5d",
    text_color: str = "#e9e9e9",
    show_value: bool = True,
    show_min_max: bool = False,
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
        threshold: Value threshold in percents
        size: Size of the SVG (width and height in pixels)
        stroke_width: Width of the gauge arc stroke
        background_color: Color of the background arc
        fill_color: Color of the filled arc
        text_color: Color of the text
        show_value: Whether to display the current value
        show_min_max: Whether to display min/max labels
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
    left_border = max(0, min(1, (value - (threshold * value / 100) - min_value) / (max_value - min_value)))
    left_border_angle = start_angle + (end_angle - start_angle) * left_border
    left_border_rad = math.radians(left_border_angle)

    right_border = max(0, min(1, (value + (threshold * value / 100) - min_value) / (max_value - min_value)))
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

    # Build SVG
    svg_parts = [
        f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size - 15}" xmlns="http://www.w3.org/2000/svg">',
        "  <defs>",
        "    <style>",
        "      .gauge-text {",
        '        font-family: "Open Sans", sans-serif;',
        "        font-size: 12px;",
        "        font-weight: bold;",
        f"        fill: {text_color};",
        "        text-anchor: middle;",
        "      }",
        "      .gauge-label {",
        '        font-family: "Open Sans", sans-serif;',
        "        font-size: 12px;",
        f"        fill: {text_color};",
        "        text-anchor: middle;",
        "      }",
        "    </style>",
        "  </defs>",
        f'  <path d="{start_arc}"',
        '        fill="none"',
        f'        stroke="{background_color}"',
        f'        stroke-width="{stroke_width}"',
        '        stroke-linecap="round"/>',
        f'  <path d="{end_arc}"',
        '        fill="none"',
        f'        stroke="{background_color}"',
        f'        stroke-width="{stroke_width}"',
        '        stroke-linecap="round"/>',
        f'  <path d="{filled_arc}"',
        '        fill="none"',
        f'        stroke="{fill_color}"',
        f'        stroke-width="{stroke_width}"',
        '        stroke-linecap="round"/>',
        f'  <circle cx="{value_x}" cy="{value_y}" r="{stroke_width}"',
        '        fill="none"',
        f'        stroke="{fill_color}"',
        f'        stroke-width="{stroke_width}"',
        '        stroke-linecap="round"/>',
    ]

    # Add value text
    if show_value:
        svg_parts.append(f'  <text x="{center_x}" y="{center_y + size // 20}" class="gauge-text">{value:.0f}</text>')

    # Add min/max labels if requested
    if show_min_max:
        min_x, min_y = point_on_circle(start_rad, radius + stroke_width // 2 + 10)
        max_x, max_y = point_on_circle(end_rad, radius + stroke_width // 2 + 10)
        svg_parts.extend(
            [
                f'  <text x="{min_x}" y="{min_y}" class="gauge-label">{min_value}</text>',
                f'  <text x="{max_x}" y="{max_y}" class="gauge-label">{max_value}</text>',
            ]
        )

    svg_parts.append("</svg>")

    return "\n".join(svg_parts)
