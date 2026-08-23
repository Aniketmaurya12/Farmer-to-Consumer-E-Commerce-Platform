"""Generate the placeholder produce images used by the seasonal sections.

Run this once after cloning:

    python create_default_images.py

The generated JPEGs are committed to the repository on purpose. Hosts such as
Vercel serve the application from a read-only filesystem, so anything created
at request time would not survive; the images have to exist in the repo.
"""

import hashlib
import os

from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = os.path.join('static', 'images', 'default')
SIZE = (800, 600)

# Fonts to try, in order of preference. The previous version asked for
# "arial.ttf" only, which does not exist on Linux (or on the deploy host), so
# every render silently fell back to Pillow's ~11px bitmap font and produced an
# essentially blank image.
FONT_CANDIDATES = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
    '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf',
    '/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf',
    '/Library/Fonts/Arial Bold.ttf',            # macOS
    'C:\\Windows\\Fonts\\arialbd.ttf',          # Windows
    'DejaVuSans-Bold.ttf',
    'arialbd.ttf',
    'arial.ttf',
]

# Approximate real produce colours so each card is visually distinct.
PRODUCE_COLORS = {
    'Carrots': (237, 125, 49),
    'Spinach': (56, 118, 60),
    'Cauliflower': (176, 166, 132),
    'Green Peas': (106, 168, 79),
    'Oranges': (245, 145, 32),
    'Apples': (192, 57, 43),
    'Guava': (140, 172, 84),
    'Cucumber': (85, 150, 74),
    'Tomatoes': (203, 60, 44),
    'Bottle Gourd': (138, 176, 106),
    'Mangoes': (233, 165, 40),
    'Watermelon': (198, 66, 74),
    'Lychee': (198, 74, 96),
    'Bitter Gourd': (74, 133, 62),
    'Lady Finger': (117, 165, 71),
    'Corn': (226, 178, 47),
    'Pomegranate': (166, 45, 58),
    'Pear': (167, 181, 74),
    'Jamun': (94, 68, 128),
    'Fresh Vegetables': (76, 141, 74),
    'Fresh Fruits': (206, 106, 51),
}


def load_font(size):
    """Return a scalable font at the requested size.

    Falls back to Pillow's built-in font, which since 10.1 accepts a size, so
    the text stays legible even when no TrueType font is installed.
    """
    for path in FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        # Pillow < 10.1: unscalable bitmap font, but still better than nothing.
        return ImageFont.load_default()


def _relative_luminance(rgb):
    """WCAG relative luminance for an 8-bit RGB triple."""
    channels = []
    for value in rgb:
        c = value / 255
        channels.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_with_white(rgb):
    """WCAG contrast ratio between white text and this background."""
    return 1.05 / (_relative_luminance(rgb) + 0.05)


def darken_for_white_text(rgb, target=4.5):
    """Darken a colour until white text on it clears the WCAG AA ratio.

    Pale produce colours (cauliflower, bottle gourd) would otherwise render
    near-white text on a near-white card.
    """
    r, g, b = rgb
    while contrast_with_white((r, g, b)) < target and max(r, g, b) > 0:
        r, g, b = int(r * 0.95), int(g * 0.95), int(b * 0.95)
    return (r, g, b)


def color_for(text):
    """Pick the produce colour, or derive a stable one from the name."""
    if text in PRODUCE_COLORS:
        base = PRODUCE_COLORS[text]
    else:
        digest = hashlib.md5(text.encode('utf-8')).digest()
        # Keep it mid-tone so white text always reads against it.
        base = (80 + digest[0] % 120, 80 + digest[1] % 120, 80 + digest[2] % 120)
    return darken_for_white_text(base)


def wrap(text, font, draw, max_width):
    """Greedy word wrap against the rendered width."""
    words = text.split()
    lines, current = [], ''
    for word in words:
        trial = f'{current} {word}'.strip()
        if draw.textlength(trial, font=font) <= max_width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def fit_font(text, draw, max_width, max_height, start=96, minimum=28):
    """Shrink the font until the wrapped text fits the available box."""
    size = start
    while size > minimum:
        font = load_font(size)
        lines = wrap(text, font, draw, max_width)
        line_height = font.getbbox('Ag')[3] - font.getbbox('Ag')[1]
        total = len(lines) * (line_height * 1.35)
        if total <= max_height and all(
            draw.textlength(line, font=font) <= max_width for line in lines
        ):
            return font, lines
        size -= 4
    font = load_font(minimum)
    return font, wrap(text, font, draw, max_width)


def create_placeholder_image(text, output_path, size=SIZE, subtitle=None):
    base = color_for(text)
    image = Image.new('RGB', size, base)
    draw = ImageDraw.Draw(image)

    # Vertical gradient: lighter at the top, deeper at the bottom.
    width, height = size
    for y in range(height):
        factor = y / height
        row = (
            int(base[0] * (1 - 0.35 * factor) + 255 * 0.12 * (1 - factor)),
            int(base[1] * (1 - 0.35 * factor) + 255 * 0.12 * (1 - factor)),
            int(base[2] * (1 - 0.35 * factor) + 255 * 0.12 * (1 - factor)),
        )
        draw.line([(0, y), (width, y)], fill=row)

    margin = int(width * 0.1)
    font, lines = fit_font(text, draw, width - 2 * margin, height * 0.45)

    line_height = font.getbbox('Ag')[3] - font.getbbox('Ag')[1]
    spacing = line_height * 1.35
    block_height = len(lines) * spacing
    y = (height - block_height) / 2 - (line_height * 0.4 if subtitle else 0)

    for line in lines:
        x = (width - draw.textlength(line, font=font)) / 2
        draw.text((x + 3, y + 3), line, font=font, fill=(0, 0, 0))
        draw.text((x, y), line, font=font, fill=(255, 255, 255))
        y += spacing

    if subtitle:
        sub_font = load_font(34)
        sub_width = draw.textlength(subtitle, font=sub_font)
        draw.text(
            ((width - sub_width) / 2, y + line_height * 0.35),
            subtitle,
            font=sub_font,
            fill=(255, 255, 255),
        )

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    image.save(output_path, quality=90, optimize=True)
    return output_path


def slugify(name):
    return name.lower().replace(' ', '_')


# Must stay in step with the seasonal_info table in app.py.
VEGETABLES = [
    'Carrots', 'Spinach', 'Cauliflower', 'Green Peas',
    'Cucumber', 'Tomatoes', 'Bottle Gourd',
    'Bitter Gourd', 'Lady Finger', 'Corn',
]
FRUITS = [
    'Oranges', 'Apples', 'Guava',
    'Mangoes', 'Watermelon', 'Lychee',
    'Pomegranate', 'Pear', 'Jamun',
]


if __name__ == '__main__':
    # Category fallbacks, referenced by the templates' onerror handler and by
    # products that were listed without a photo.
    create_placeholder_image(
        'Fresh Vegetables', os.path.join(OUTPUT_DIR, 'vegetables.jpg')
    )
    create_placeholder_image(
        'Fresh Fruits', os.path.join(OUTPUT_DIR, 'fruits.jpg')
    )

    for name in VEGETABLES:
        create_placeholder_image(
            name, os.path.join(OUTPUT_DIR, f'{slugify(name)}.jpg'),
            subtitle='Vegetable',
        )
    for name in FRUITS:
        create_placeholder_image(
            name, os.path.join(OUTPUT_DIR, f'{slugify(name)}.jpg'),
            subtitle='Fruit',
        )

    total = len(VEGETABLES) + len(FRUITS) + 2
    print(f'Generated {total} images in {OUTPUT_DIR}')
