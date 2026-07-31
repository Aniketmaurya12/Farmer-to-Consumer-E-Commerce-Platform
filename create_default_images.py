from PIL import Image, ImageDraw, ImageFont
import os

def create_placeholder_image(text, output_path, size=(800, 600), bg_color=(248, 249, 250), text_color=(33, 37, 41)):
    # Create a new image with a light background
    image = Image.new('RGB', size, bg_color)
    draw = ImageDraw.Draw(image)
    
    # Add a subtle gradient
    for y in range(size[1]):
        for x in range(size[0]):
            # Create a subtle gradient effect
            factor = y / size[1]
            r = int(bg_color[0] * (1 - factor * 0.1))
            g = int(bg_color[1] * (1 - factor * 0.1))
            b = int(bg_color[2] * (1 - factor * 0.1))
            draw.point((x, y), fill=(r, g, b))
    
    # Try to use a nice font, fall back to default if not available
    try:
        font = ImageFont.truetype("arial.ttf", 48)
    except:
        font = ImageFont.load_default()
    
    # Calculate text position (center)
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    x = (size[0] - text_width) // 2
    y = (size[1] - text_height) // 2
    
    # Add a subtle shadow effect
    shadow_offset = 2
    draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=(0, 0, 0, 100))
    
    # Draw main text
    draw.text((x, y), text, font=font, fill=text_color)
    
    # Save the image with high quality
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    image.save(output_path, quality=95, optimize=True)

if __name__ == "__main__":
    # Create default images with larger dimensions and better quality
    create_placeholder_image("Fresh Vegetables", "static/images/default/vegetables.jpg")
    create_placeholder_image("Fresh Fruits", "static/images/default/fruits.jpg")
