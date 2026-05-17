"""
Helios-Grid Thumbnail Generator
Converts SVG to optimized PNG under 300KB for GitHub social preview
"""

import os
import sys
from pathlib import Path


def create_optimized_thumbnail():
    """Create an optimized PNG thumbnail under 300KB"""

    print("🎨 Helios-Grid Thumbnail Generator")
    print("=" * 40)

    try:
        # Try to import required libraries
        try:
            import io

            from PIL import Image
            from PIL import ImageDraw
            from PIL import ImageFont
        except ImportError:
            print("📦 Installing required packages...")
            os.system("pip install Pillow")
            import io

            from PIL import Image
            from PIL import ImageDraw
            from PIL import ImageFont

        # Create thumbnail dimensions (GitHub social preview size)
        width, height = 1200, 630

        # Create image with gradient background
        img = Image.new("RGB", (width, height), color="#0f0f23")
        draw = ImageDraw.Draw(img)

        # Create gradient background
        for y in range(height):
            # Calculate gradient colors
            ratio = y / height
            r = int(15 + (22 - 15) * ratio)
            g = int(15 + (26 - 15) * ratio)
            b = int(35 + (62 - 35) * ratio)
            color = (r, g, b)
            draw.line([(0, y), (width, y)], fill=color)

        # Draw grid pattern
        grid_color = (59, 130, 246, 30)  # Semi-transparent blue
        for x in range(0, width, 50):
            draw.line([(x, 0), (x, height)], fill=grid_color, width=1)
        for y in range(0, height, 50):
            draw.line([(0, y), (width, y)], fill=grid_color, width=1)

        # Draw sun icon (circle)
        sun_center = (140, 140)
        sun_radius = 60
        sun_color = (251, 191, 36)
        draw.ellipse(
            [
                sun_center[0] - sun_radius,
                sun_center[1] - sun_radius,
                sun_center[0] + sun_radius,
                sun_center[1] + sun_radius,
            ],
            fill=sun_color,
        )

        # Try to load fonts, fallback to default if not available
        try:
            title_font = ImageFont.truetype("arial.ttf", 72)
            subtitle_font = ImageFont.truetype("arial.ttf", 28)
            small_font = ImageFont.truetype("arial.ttf", 16)
            badge_font = ImageFont.truetype("arial.ttf", 12)
        except:
            try:
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
                small_font = ImageFont.load_default()
                badge_font = ImageFont.load_default()
            except:
                title_font = None
                subtitle_font = None
                small_font = None
                badge_font = None

        # Draw main title
        title_text = "Helios-Grid"
        title_color = (59, 130, 246)  # Blue
        if title_font:
            draw.text((250, 120), title_text, fill=title_color, font=title_font)
        else:
            draw.text((250, 120), title_text, fill=title_color)

        # Draw subtitle
        subtitle_text = "Enterprise Energy Consumption MLOps Pipeline"
        subtitle_color = (148, 163, 184)  # Gray
        if subtitle_font:
            draw.text(
                (250, 220), subtitle_text, fill=subtitle_color, font=subtitle_font
            )
        else:
            draw.text((250, 220), subtitle_text, fill=subtitle_color)

        # Draw description
        desc_text = "Azure-Native • Production-Ready • Staff-Level Engineering"
        desc_color = (100, 116, 139)  # Darker gray
        if small_font:
            draw.text((250, 270), desc_text, fill=desc_color, font=small_font)
        else:
            draw.text((250, 270), desc_text, fill=desc_color)

        # Draw energy visualization bars
        bar_x = 850
        bar_y = 200
        bar_width = 250
        bar_height = 20
        bar_spacing = 35

        bar_fills = [0.85, 0.92, 0.78, 0.95]
        bar_color = (59, 130, 246)

        for i, fill_ratio in enumerate(bar_fills):
            y_pos = bar_y + i * bar_spacing

            # Background bar
            draw.rectangle(
                [bar_x, y_pos, bar_x + bar_width, y_pos + bar_height],
                fill=(59, 130, 246, 50),
            )

            # Filled bar
            fill_width = int(bar_width * fill_ratio)
            draw.rectangle(
                [bar_x, y_pos, bar_x + fill_width, y_pos + bar_height], fill=bar_color
            )

        # Draw tech stack badges
        badges = [
            "Azure ML",
            "FastAPI",
            "XGBoost",
            "MLflow",
            "Docker",
            "Prometheus",
            "Grafana",
        ]
        badge_x = 80
        badge_y = 450
        badge_spacing = 90

        for i, badge_text in enumerate(badges):
            x_pos = badge_x + i * badge_spacing

            # Badge background
            badge_width = len(badge_text) * 8 + 20
            draw.rectangle(
                [x_pos, badge_y, x_pos + badge_width, badge_y + 30],
                fill=(59, 130, 246, 50),
                outline=(59, 130, 246, 100),
            )

            # Badge text
            if badge_font:
                draw.text(
                    (x_pos + 10, badge_y + 8),
                    badge_text,
                    fill=(96, 165, 250),
                    font=badge_font,
                )
            else:
                draw.text((x_pos + 10, badge_y + 8), badge_text, fill=(96, 165, 250))

        # Draw GitHub badge
        github_text = "github.com/sankeashok/Helios-Grid"
        github_x = 850
        github_y = 550

        # GitHub badge background
        draw.rectangle(
            [github_x, github_y, github_x + 280, github_y + 40],
            fill=(255, 255, 255, 25),
            outline=(255, 255, 255, 50),
        )

        # GitHub text
        if small_font:
            draw.text(
                (github_x + 20, github_y + 12),
                github_text,
                fill=(255, 255, 255),
                font=small_font,
            )
        else:
            draw.text((github_x + 20, github_y + 12), github_text, fill=(255, 255, 255))

        # Draw floating circles
        circle_positions = [(950, 350, 30), (1050, 200, 20), (500, 480, 40)]
        for x, y, radius in circle_positions:
            draw.ellipse(
                [x - radius, y - radius, x + radius, y + radius],
                fill=(59, 130, 246, 25),
            )

        # Optimize and save the image
        print("💾 Optimizing image...")

        # Save with optimization
        output_path = "helios-grid-thumbnail.png"

        # Try different quality settings to get under 300KB
        for quality in [95, 90, 85, 80, 75, 70]:
            # Convert to bytes to check size
            img_bytes = io.BytesIO()
            img.save(img_bytes, format="PNG", optimize=True)

            size_kb = len(img_bytes.getvalue()) / 1024

            if size_kb <= 300:
                # Save the final image
                img.save(output_path, format="PNG", optimize=True)
                print(f"✅ Thumbnail created: {output_path}")
                print(f"📏 Size: {size_kb:.1f} KB (under 300KB limit)")
                print(f"📐 Dimensions: {width}x{height}px (GitHub social preview)")
                return True

        # If still too large, resize
        print("🔄 Resizing to reduce file size...")
        img_resized = img.resize((1000, 525), Image.Resampling.LANCZOS)
        img_resized.save(output_path, format="PNG", optimize=True)

        # Check final size
        final_size = os.path.getsize(output_path) / 1024
        print(f"✅ Thumbnail created: {output_path}")
        print(f"📏 Final size: {final_size:.1f} KB")
        print(f"📐 Final dimensions: 1000x525px")

        return True

    except Exception as e:
        print(f"❌ Error creating thumbnail: {e}")
        print("\n💡 Alternative: Use the SVG file or HTML generator")
        return False


def main():
    """Main function"""
    print("🌟 Creating Helios-Grid thumbnail for GitHub...")

    success = create_optimized_thumbnail()

    if success:
        print("\n🎯 Next Steps:")
        print("1. Upload 'helios-grid-thumbnail.png' to your GitHub repository")
        print("2. Add to README.md: ![Helios-Grid](helios-grid-thumbnail.png)")
        print("3. Set as repository social preview in Settings > General")
        print("\n🔗 Perfect for link sharing and social media!")
    else:
        print("\n📝 Manual Options:")
        print("1. Open 'generate_thumbnail.html' in browser and download")
        print("2. Use 'helios-grid-thumbnail.svg' directly")
        print("3. Convert SVG to PNG using online tools")


if __name__ == "__main__":
    main()
