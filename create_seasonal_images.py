"""
Generates one picture per seasonal item for the home page.

Run once:  python create_seasonal_images.py

It writes SVG artwork into static/images/seasonal/<slug>.svg

If you would rather use REAL PHOTOS, just drop a photo into the same
folder named after the item, e.g.:

    static/images/seasonal/tomatoes.jpg
    static/images/seasonal/mangoes.png

app.py prefers a real photo (.jpg/.jpeg/.png/.webp) over the drawing,
so nothing else needs changing.
"""

import os

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       'static', 'images', 'seasonal')


def frame(bg1, bg2, body):
    """Wrap artwork in a consistent 600x400 card background."""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 400" width="600" height="400">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{bg1}"/>
      <stop offset="100%" stop-color="{bg2}"/>
    </linearGradient>
    <radialGradient id="glow" cx="50%" cy="45%" r="55%">
      <stop offset="0%" stop-color="#ffffff" stop-opacity="0.55"/>
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="600" height="400" fill="url(#bg)"/>
  <circle cx="300" cy="200" r="170" fill="url(#glow)"/>
  <ellipse cx="300" cy="348" rx="140" ry="20" fill="#000000" opacity="0.10"/>
{body}
</svg>
'''


def leaf(x, y, rot, fill='#3d8b37', scale=1.0):
    return (f'<path transform="translate({x},{y}) rotate({rot}) scale({scale})" '
            f'd="M0,0 C 30,-34 78,-38 96,-8 C 66,26 22,28 0,0 Z" fill="{fill}"/>')


def stem(x, y, w=12, h=46, fill='#4a7c2f', rot=0):
    return (f'<rect transform="translate({x},{y}) rotate({rot})" x="{-w/2}" y="{-h}" '
            f'width="{w}" height="{h}" rx="{w/2}" fill="{fill}"/>')


def round_fruit(cx, cy, r, fill, dark, light='#ffffff'):
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}"/>'
            f'<path d="M{cx-r},{cy} a{r},{r} 0 0 0 {2*r},0 a{r},{r} 0 0 0 {-2*r},0 Z" fill="{dark}" opacity="0.25"/>'
            f'<ellipse cx="{cx-r*0.34}" cy="{cy-r*0.40}" rx="{r*0.26}" ry="{r*0.18}" '
            f'fill="{light}" opacity="0.55" transform="rotate(-25 {cx-r*0.34} {cy-r*0.40})"/>')


ART = {}

# ---------------------------------------------------------------- winter veg
ART['carrots'] = frame('#fff4e6', '#ffe2c2', ''.join([
    f'<g transform="translate(300,215) rotate({a})">'
    f'<path d="M{-38+o},-70 L{38+o},-70 L{6+o},120 C {2+o},132 {-2+o},132 {-6+o},120 Z" fill="#f0761e"/>'
    f'<path d="M{-38+o},-70 L{0+o},-70 L{0+o},120 C {-2+o},128 {-5+o},128 {-6+o},120 Z" fill="#ff9540" opacity="0.7"/>'
    f'<path d="M{-26+o},-30 L{26+o},-24" stroke="#d35f12" stroke-width="4" stroke-linecap="round" opacity="0.6"/>'
    f'<path d="M{-20+o},10 L{20+o},16" stroke="#d35f12" stroke-width="4" stroke-linecap="round" opacity="0.6"/>'
    f'</g>'
    for a, o in ((-16, -78), (0, 0), (16, 78))
]) + ''.join([
    leaf(300 + dx, 148, r, '#3f8f34', 0.55) for dx, r in ((-72, 200), (-24, 232), (24, 300), (72, 335))
]))

ART['spinach'] = frame('#eef7e8', '#d7ecd0', ''.join([
    f'<path transform="translate(300,250) rotate({r})" d="M0,0 C 46,-96 148,-104 176,-30 C 128,44 40,44 0,0 Z" '
    f'fill="{c}"/><path transform="translate(300,250) rotate({r})" d="M6,-4 C 60,-40 120,-46 160,-34" '
    f'stroke="#2f6b28" stroke-width="5" fill="none" stroke-linecap="round"/>'
    for r, c in ((178, '#2f7a2b'), (215, '#3f9436'), (250, '#4faa41'),
                 (285, '#3f9436'), (320, '#2f7a2b'))
]) + '<circle cx="300" cy="250" r="18" fill="#2b6624"/>')

ART['cauliflower'] = frame('#f6f8f2', '#e3ecdc',
    # outer leaves cupping the head
    ''.join(f'<path transform="translate(300,268) rotate({r})" d="M0,0 C 40,-80 132,-92 158,-24 '
            f'C 120,50 34,52 0,0 Z" fill="{c}"/>' for r, c in
            ((166, '#357a30'), (200, '#3f8f34'), (232, '#4a9c40'),
             (308, '#4a9c40'), (340, '#3f8f34'), (14, '#357a30'))) +
    # curd head
    ''.join(f'<circle cx="{300+dx}" cy="{206+dy}" r="{rr}" fill="#f3efdd"/>'
            for dx, dy, rr in ((0, 0, 96), (-72, 20, 58), (72, 20, 58), (-44, -50, 52),
                               (46, -52, 50), (0, -72, 52), (0, 52, 58))) +
    ''.join(f'<circle cx="{300+dx}" cy="{206+dy}" r="{rr}" fill="#fffdf0"/>'
            for dx, dy, rr in ((-34, -26, 30), (32, -20, 28), (0, 24, 32), (-64, 22, 24),
                               (64, 22, 24), (0, -56, 26), (-16, -6, 20), (46, -50, 20))))

ART['green-peas'] = frame('#f0f9ea', '#d8efcd',
    '<path d="M150,246 C 176,150 424,150 450,246 C 424,318 176,318 150,246 Z" fill="#4fa83f"/>'
    '<path d="M150,246 C 176,168 424,168 450,246 C 400,228 200,228 150,246 Z" fill="#63c04f"/>' +
    ''.join(round_fruit(cx, 248, 34, '#7fd15f', '#4c9a3a') for cx in (206, 274, 342, 410)) +
    stem(146, 250, 12, 40, '#3f8b31', -70) + leaf(452, 214, -30, '#3f8b31', 0.5))

# -------------------------------------------------------------- winter fruit
ART['oranges'] = frame('#fff5e2', '#ffe0b3',
    round_fruit(238, 244, 86, '#f9a01b', '#d97b06') +
    round_fruit(372, 214, 74, '#ffb52e', '#e08a10') +
    ''.join(f'<path d="M372,214 L{372+70*c},{214+70*s}" stroke="#ffffff" stroke-width="3" opacity="0.35"/>'
            for c, s in ((1, 0), (0.5, 0.87), (-0.5, 0.87), (-1, 0), (-0.5, -0.87), (0.5, -0.87))) +
    stem(238, 160, 12, 30, '#6b4a1e') + leaf(246, 150, -18, '#3f8f34', 0.5))

ART['apples'] = frame('#fff1f1', '#ffd9d9',
    '<path d="M300,148 C 236,120 176,168 182,236 C 188,306 244,352 300,352 C 356,352 412,306 418,236 '
    'C 424,168 364,120 300,148 Z" fill="#e0342f"/>'
    '<path d="M300,148 C 262,132 224,158 212,204 C 200,254 224,314 262,340 C 226,300 214,238 232,196 '
    'C 246,162 272,146 300,148 Z" fill="#f4564f" opacity="0.85"/>'
    '<ellipse cx="256" cy="196" rx="26" ry="18" fill="#ffffff" opacity="0.45" transform="rotate(-30 256 196)"/>' +
    stem(300, 156, 11, 44, '#6b4a1e') + leaf(306, 128, -20, '#3f8f34', 0.55))

ART['guava'] = frame('#f3f9ea', '#dcefc9',
    round_fruit(300, 236, 108, '#c3d94e', '#94b032') +
    '<path d="M300,150 C 268,178 258,222 268,262" stroke="#a9c33c" stroke-width="6" fill="none" opacity="0.6"/>'
    '<path d="M300,150 C 334,178 344,222 334,262" stroke="#a9c33c" stroke-width="6" fill="none" opacity="0.6"/>' +
    ''.join(f'<path d="M300,136 l{dx},-6 l0,12 Z" fill="#8aa82c"/>' for dx in (-16, 16)) +
    stem(300, 140, 10, 26, '#7d6b2c') + leaf(306, 126, -24, '#3f8f34', 0.5))

# ---------------------------------------------------------------- summer veg
ART['cucumber'] = frame('#eefaf0', '#d2f0da',
    '<g transform="translate(300,230) rotate(-22)">'
    '<rect x="-186" y="-56" width="372" height="112" rx="56" fill="#2f7d3e"/>'
    '<rect x="-186" y="-56" width="372" height="56" rx="28" fill="#3f9b4d" opacity="0.8"/>' +
    ''.join(f'<ellipse cx="{x}" cy="{y}" rx="7" ry="5" fill="#8fd39a" opacity="0.75"/>'
            for x, y in ((-130, -18), (-70, 10), (-10, -22), (50, 12), (110, -14), (150, 16),
                         (-100, 24), (20, 26), (140, -30))) +
    '</g>' + stem(302, 118, 12, 30, '#4a7c2f', -22) + leaf(316, 104, -46, '#3f8f34', 0.5))

ART['tomatoes'] = frame('#fff0ee', '#ffd6d0',
    round_fruit(246, 250, 92, '#e33b2e', '#b8231a') +
    round_fruit(378, 224, 68, '#f24b3a', '#c22c1f') +
    '<path d="M246,166 l-46,-16 l24,30 l-34,4 l38,20 l18,-22 l18,22 l38,-20 l-34,-4 l24,-30 Z" fill="#3f8f34"/>' +
    stem(246, 168, 10, 26, '#3f8f34'))

ART['bottle-gourd'] = frame('#f1faec', '#d7efcb',
    '<path d="M300,120 C 268,120 258,166 268,196 C 216,230 200,300 254,336 C 300,366 356,352 376,306 '
    'C 396,258 366,214 332,196 C 342,166 332,120 300,120 Z" fill="#5aa83f"/>'
    '<path d="M292,132 C 274,148 274,182 286,200 C 244,228 232,286 268,318 C 244,278 254,232 296,206 '
    'C 282,186 280,152 292,132 Z" fill="#79c65a" opacity="0.85"/>' +
    stem(300, 124, 12, 34, '#4a7c2f') + leaf(306, 106, -26, '#3f8f34', 0.5))

# -------------------------------------------------------------- summer fruit
ART['mangoes'] = frame('#fff8e1', '#ffe6ab',
    # back mango
    '<g transform="translate(386,222) rotate(24)">'
    '<path d="M0,-84 C 62,-84 96,-26 84,32 C 74,80 26,96 -14,76 C -62,52 -76,-14 -50,-56 '
    'C -38,-76 -20,-84 0,-84 Z" fill="#e8951a"/>'
    '<path d="M40,-62 C 74,-24 76,32 52,66 C 84,30 82,-28 40,-62 Z" fill="#d2521f" opacity="0.7"/>'
    '</g>'
    # front mango: fat top, tapering beak at bottom-right
    '<g transform="translate(258,240) rotate(-14)">'
    '<path d="M-8,-96 C 66,-96 106,-30 92,38 C 80,96 22,120 -26,96 C -84,66 -100,-16 -66,-64 '
    'C -50,-86 -30,-96 -8,-96 Z" fill="#f7b322"/>'
    '<path d="M-8,-96 C -56,-84 -84,-24 -70,32 C -60,72 -34,96 -4,104 C -48,92 -74,50 -76,4 '
    'C -78,-46 -50,-86 -8,-96 Z" fill="#ffd35e" opacity="0.95"/>'
    '<path d="M52,-62 C 92,-20 96,44 66,86 C 104,48 104,-20 52,-62 Z" fill="#e0521f" opacity="0.75"/>'
    '<ellipse cx="-40" cy="-38" rx="30" ry="17" fill="#ffffff" opacity="0.45" transform="rotate(-38 -40 -38)"/>'
    '</g>' +
    stem(252, 152, 10, 30, '#6b4a1e', -10) + leaf(260, 132, -26, '#3f8f34', 0.55))

ART['watermelon'] = frame('#f0fbef', '#d3f0d2',
    '<path d="M120,268 A 180,180 0 0 1 480,268 Z" fill="#2f7d3e"/>'
    '<path d="M136,268 A 164,164 0 0 1 464,268 Z" fill="#f4f8e6"/>'
    '<path d="M152,268 A 148,148 0 0 1 448,268 Z" fill="#e8443e"/>' +
    ''.join(f'<ellipse cx="{x}" cy="{y}" rx="7" ry="11" fill="#2b2b2b"/>'
            for x, y in ((222, 216), (282, 190), (344, 202), (392, 238),
                         (246, 254), (312, 246), (372, 258), (196, 250))) +
    ''.join(f'<path d="M{x},268 A 180,180 0 0 1 {x2},268" fill="none" stroke="#1f5e2c" '
            f'stroke-width="0" />' for x, x2 in ()))

def _lychee(cx, cy, r):
    """Bumpy pink-red lychee with a rough skin texture."""
    import math
    bumps = ''.join(
        f'<circle cx="{cx + r*0.72*math.cos(math.radians(a)):.1f}" '
        f'cy="{cy + r*0.72*math.sin(math.radians(a)):.1f}" r="{r*0.17:.1f}" '
        f'fill="#f27a86" opacity="0.9"/>' for a in range(0, 360, 40))
    inner = ''.join(
        f'<circle cx="{cx + r*0.34*math.cos(math.radians(a)):.1f}" '
        f'cy="{cy + r*0.34*math.sin(math.radians(a)):.1f}" r="{r*0.15:.1f}" '
        f'fill="#f9959e" opacity="0.85"/>' for a in range(20, 380, 60))
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#d94b5c"/>' + bumps + inner +
            f'<circle cx="{cx}" cy="{cy}" r="{r*0.14}" fill="#fbb0b7" opacity="0.9"/>')


ART['lychee'] = frame('#fff0f2', '#ffd4da',
    _lychee(252, 258, 76) + _lychee(372, 230, 60) + _lychee(320, 330, 40) +
    stem(252, 186, 9, 26, '#7a4a22') + leaf(260, 172, -24, '#3f8f34', 0.45))

# --------------------------------------------------------------- monsoon veg
ART['bitter-gourd'] = frame('#eff8e6', '#d4ecc2',
    '<g transform="translate(300,236) rotate(-18)">'
    '<path d="M-170,0 C -150,-70 150,-80 172,-6 C 152,66 -148,64 -170,0 Z" fill="#4f9a2f"/>'
    '<path d="M-170,0 C -150,-52 150,-60 172,-6 C 120,-30 -110,-28 -170,0 Z" fill="#6fbb45" opacity="0.85"/>' +
    ''.join(f'<path d="M{x},-42 C {x+12},-14 {x+12},14 {x},44" stroke="#2f6b1c" stroke-width="7" '
            f'fill="none" stroke-linecap="round" opacity="0.75"/>' for x in range(-140, 160, 34)) +
    '</g>' + stem(302, 128, 12, 30, '#4a7c2f', -18) + leaf(316, 114, -44, '#3f8f34', 0.5))

ART['lady-finger'] = frame('#f0f9e8', '#d6eec5', ''.join([
    f'<g transform="translate(300,220) rotate({a})">'
    f'<path d="M{o},-104 C {o+34},-70 {o+38},60 {o+10},124 C {o-8},130 {o-22},126 {o-26},116 '
    f'C {o-6},50 {o-8},-64 {o-22},-102 Z" fill="{c}"/>'
    f'<path d="M{o-4},-92 C {o+6},-30 {o+6},50 {o-2},110" stroke="#2f6b1c" stroke-width="4" '
    f'fill="none" opacity="0.55"/>'
    f'<rect x="{o-26}" y="-124" width="22" height="26" rx="8" fill="#3f7f28"/>'
    f'</g>'
    for a, o, c in ((-14, -86, '#68b53c'), (0, 0, '#7cc94a'), (14, 86, '#68b53c'))
]))

ART['corn'] = frame('#fffae6', '#ffefbe',
    '<g transform="translate(300,220) rotate(-10)">'
    '<rect x="-58" y="-134" width="116" height="268" rx="58" fill="#f5c518"/>' +
    ''.join(f'<circle cx="{x}" cy="{y}" r="12" fill="#ffe066" stroke="#e0a800" stroke-width="2"/>'
            for y in range(-108, 120, 26)
            for x in ((-36, -12, 12, 36) if (y // 26) % 2 == 0 else (-24, 0, 24))) +
    '<path d="M-58,-100 C -140,-40 -130,90 -46,124 C -84,60 -86,-30 -58,-100 Z" fill="#4f9a2f"/>'
    '<path d="M58,-100 C 140,-40 130,90 46,124 C 84,60 86,-30 58,-100 Z" fill="#5fae38"/>'
    '</g>')

# ------------------------------------------------------------- monsoon fruit
ART['pomegranate'] = frame('#fff0f0', '#ffd3d3',
    round_fruit(288, 246, 104, '#c62828', '#8e1b1b') +
    '<path d="M288,148 l-16,-30 l16,10 l16,-10 Z" fill="#a01d1d"/>'
    '<path d="M288,142 l-30,-34 l30,14 l30,-14 Z" fill="#8e1b1b"/>'
    '<path d="M380,278 A 104,104 0 0 1 300,344 L300,246 Z" fill="#f4f0e2" opacity="0.95"/>' +
    ''.join(f'<circle cx="{cx}" cy="{cy}" r="9" fill="#e0333a"/>'
            for cx, cy in ((320, 276), (342, 288), (318, 302), (340, 314), (316, 326), (356, 306))))

ART['pear'] = frame('#f8fbe8', '#e7f2c4',
    '<path d="M300,140 C 274,140 264,170 276,192 C 236,214 214,266 232,306 C 252,352 348,352 368,306 '
    'C 386,266 364,214 324,192 C 336,170 326,140 300,140 Z" fill="#c8d94a"/>'
    '<path d="M292,152 C 278,168 280,188 290,198 C 250,224 236,270 250,304 C 238,262 254,220 300,196 '
    'C 288,184 284,164 292,152 Z" fill="#dcea6e" opacity="0.9"/>'
    '<ellipse cx="268" cy="264" rx="24" ry="34" fill="#ffffff" opacity="0.35" transform="rotate(-18 268 264)"/>' +
    stem(300, 146, 10, 34, '#6b4a1e') + leaf(306, 124, -24, '#3f8f34', 0.5))

ART['jamun'] = frame('#f3eefb', '#ddd0f0',
    ''.join(f'<g transform="translate({cx},{cy}) rotate({rot})">'
            f'<ellipse cx="0" cy="0" rx="{r}" ry="{r*1.35}" fill="#4a2a6b"/>'
            f'<ellipse cx="0" cy="{-r*0.3}" rx="{r*0.85}" ry="{r*0.75}" fill="#6a3f93" opacity="0.75"/>'
            f'<ellipse cx="{-r*0.35}" cy="{-r*0.55}" rx="{r*0.24}" ry="{r*0.16}" fill="#ffffff" '
            f'opacity="0.5" transform="rotate(-25)"/></g>'
            for cx, cy, r, rot in ((252, 258, 56, -12), (360, 232, 46, 10), (312, 316, 34, 4))) +
    stem(252, 190, 9, 26, '#4a7c2f', -12) + leaf(262, 176, -30, '#3f8f34', 0.45))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for slug, svg in ART.items():
        path = os.path.join(OUT_DIR, slug + '.svg')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(svg)
        print('wrote', path)
    print(f'\n{len(ART)} seasonal pictures created in {OUT_DIR}')


if __name__ == '__main__':
    main()
