#!/usr/bin/env python3
"""
Gerador de capas PNG do blog Consorflow (Pillow).

Capa editorial 1200x630 na identidade da marca (gradiente navy, glow do pilar,
título grande). PNG = formato aceito por Google (structured data) e redes
sociais (OG), e renderizável em qualquer ambiente (local + rotina cloud).

Uso (standalone):
    python3 gerar_capa.py "Título do post" "Pilar" saida.png

Uso (import):
    from gerar_capa import render_capa
    render_capa(title, pillar, "saida.png")
"""
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1200, 630
NAVY_TOP = (0, 41, 93)      # #00295d
NAVY_BOT = (0, 22, 50)      # #001632
TEAL = (46, 143, 176)       # #2E8FB0
WHITE = (255, 255, 255)
INK = (207, 224, 243)       # #cfe0f3

PILLAR_ACCENT = {
    "Notícias do mundo": (91, 200, 232),
    "Mundo do consórcio": (123, 211, 137),
    "Tecnologia": (157, 141, 241),
}

# Candidatos de fonte: macOS, Linux (cloud) e fallback do Pillow.
BOLD = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "DejaVuSans-Bold.ttf",
]
SEMI = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "DejaVuSans.ttf",
]


def _font(cands, size):
    for p in cands:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:4]


def render_capa(title, pillar="Consorflow", out_path="capa.png"):
    accent = PILLAR_ACCENT.get(pillar, TEAL)

    # Gradiente vertical navy
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / H
        d.line([(0, y), (W, y)], fill=tuple(
            int(NAVY_TOP[i] + (NAVY_BOT[i] - NAVY_TOP[i]) * t) for i in range(3)))
    img = img.convert("RGBA")

    # Glow do pilar (canto sup. direito)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse([800, -220, 1420, 400], fill=accent + (70,))
    glow = glow.filter(ImageFilter.GaussianBlur(140))
    img = Image.alpha_composite(img, glow)

    # Círculos decorativos + onda
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for r in (220, 320):
        od.ellipse([1040 - r, 120 - r, 1040 + r, 120 + r],
                   outline=TEAL + (32,), width=2)
    od.ellipse([1120 - 140, 560 - 140, 1120 + 140, 560 + 140],
               outline=TEAL + (28,), width=2)
    od.polygon([(0, 470), (300, 430), (700, 500), (1200, 440),
                (1200, 630), (0, 630)], fill=accent + (20,))

    # Pill do pilar (desenhado no overlay p/ alpha fazer blend)
    f_pill = _font(BOLD, 18)
    label = pillar.upper()
    tw = od.textlength(label, font=f_pill)
    od.rounded_rectangle([80, 68, 80 + tw + 40, 112], radius=22,
                         fill=accent + (46,), outline=accent + (160,), width=2)

    img = Image.alpha_composite(img, ov)
    d = ImageDraw.Draw(img)
    d.text((100, 80), label, font=f_pill, fill=accent)  # texto opaco, legível

    # Título (auto-fit)
    for fs in (62, 56, 50, 44):
        f_title = _font(BOLD, fs)
        lines = _wrap(d, title, f_title, W - 160)
        lh = int(fs * 1.16)
        if lh * len(lines) <= 320:
            break
    block_h = lh * len(lines)
    y = (H // 2) - (block_h // 2) - 10
    for ln in lines:
        d.text((80, y), ln, font=f_title, fill=WHITE)
        y += lh

    # Rodapé: dot + consorflow.com/blog
    d.ellipse([80, H - 78, 98, H - 60], fill=TEAL)
    f_foot = _font(BOLD, 22)
    x = 112
    for seg, col in [("consorflow", INK), (".com", accent), ("/blog", INK)]:
        d.text((x, H - 80), seg, font=f_foot, fill=col)
        x += d.textlength(seg, font=f_foot)

    img.convert("RGB").save(out_path, "PNG", optimize=True)
    return out_path


def main():
    if len(sys.argv) < 4:
        print('Uso: python3 gerar_capa.py "Título" "Pilar" saida.png')
        return 1
    out = render_capa(sys.argv[1], sys.argv[2], sys.argv[3])
    print(f"OK capa: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
