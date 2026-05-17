"""
Helios-Grid Thumbnail Generator - Simple Version
Creates optimized PNG under 300KB for GitHub social preview
"""

import os
from PIL import Image, ImageDraw, ImageFont
import io


def create_thumbnail():
    """Create optimized thumbnail"""
    print("Creating Helios-Grid thumbnail...")

    # Create image
    width, height = 1200, 630
    img = Image.new("RGB", (width, height), color="#0f0f23")
    draw = ImageDraw.Draw(img)

    # Gradient background
    for y in range(height):
        ratio = y / height
        r = int(15 + (22 - 15) * ratio)
        g = int(15 + (26 - 15) * ratio)
        b = int(35 + (62 - 35) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Sun circle
    draw.ellipse([80, 80, 200, 200], fill=(251, 191, 36))

    # Title
    try:
        font_large = ImageFont.truetype("arial.ttf", 72)
        font_medium = ImageFont.truetype("arial.ttf", 28)
        font_small = ImageFont.truetype("arial.ttf", 16)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    draw.text((250, 120), "Helios-Grid", fill=(59, 130, 246), font=font_large)
    draw.text(
        (250, 220),
        "Enterprise Energy Consumption MLOps Pipeline",
        fill=(148, 163, 184),
        font=font_medium,
    )
    draw.text(
        (250, 270),
        "Azure-Native • Production-Ready • Staff-Level Engineering",
        fill=(100, 116, 139),
        font=font_small,
    )

    # Energy bars
    bar_x, bar_y = 850, 200
    for i, fill_ratio in enumerate([0.85, 0.92, 0.78, 0.95]):
        y_pos = bar_y + i * 35
        draw.rectangle([bar_x, y_pos, bar_x + 250, y_pos + 20], fill=(59, 130, 246, 50))
        draw.rectangle(
            [bar_x, y_pos, bar_x + int(250 * fill_ratio), y_pos + 20],
            fill=(59, 130, 246),
        )

    # Tech badges
    badges = ["Azure ML", "FastAPI", "XGBoost", "MLflow", "Docker"]
    for i, badge in enumerate(badges):
        x_pos = 80 + i * 90
        draw.rectangle([x_pos, 450, x_pos + 80, 480], fill=(59, 130, 246, 50))
        draw.text((x_pos + 10, 458), badge, fill=(96, 165, 250), font=font_small)

    # GitHub badge
    draw.rectangle([850, 550, 1130, 590], fill=(255, 255, 255, 25))
    draw.text(
        (870, 562),
        "github.com/sankeashok/Helios-Grid",
        fill=(255, 255, 255),
        font=font_small,
    )

    # Save optimized
    output_path = "helios-grid-thumbnail.png"
    img.save(output_path, format="PNG", optimize=True)

    # Check size
    size_kb = os.path.getsize(output_path) / 1024
    print(f"Thumbnail created: {output_path}")
    print(f"Size: {size_kb:.1f} KB")
    print(f"Dimensions: {width}x{height}px")

    return output_path


if __name__ == "__main__":
    try:
        thumbnail_path = create_thumbnail()
        print("Success! Ready for GitHub.")
    except Exception as e:
        print(f"Error: {e}")
        print("Please install Pillow: pip install Pillow")
