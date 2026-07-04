#!/usr/bin/env python3
"""
Gerador de capas PNG do blog Consorflow (Pillow).

Capa editorial 1200x630 na identidade da marca, desenhada para continuar
legível quando recortada em thumbs 16:9. PNG = formato aceito por Google
(structured data) e redes sociais (OG), e renderizável em qualquer ambiente.

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


def _wrap(draw, text, font, max_w, max_lines=3):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
            if draw.textlength(cur, font=font) > max_w:
                return None
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        return None
    return lines


def _fit_title(draw, title, max_w, max_h):
    for fs in (100, 96, 92, 88, 84, 80, 76, 72, 68):
        font = _font(BOLD, fs)
        lines = _wrap(draw, title, font, max_w, max_lines=3)
        if not lines:
            continue
        lh = int(fs * 1.08)
        if lh * len(lines) <= max_h:
            return font, fs, lines, lh
    font = _font(BOLD, 64)
    lines = _wrap(draw, title, font, max_w, max_lines=3) or [title]
    return font, 64, lines[:3], int(64 * 1.08)


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

    # Círculos decorativos + onda fora do conteúdo crítico.
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for r in (220, 320):
        od.ellipse([1040 - r, 120 - r, 1040 + r, 120 + r],
                   outline=TEAL + (32,), width=2)
    od.ellipse([1120 - 140, 560 - 140, 1120 + 140, 560 + 140],
               outline=TEAL + (28,), width=2)
    od.polygon([(0, 470), (300, 430), (700, 500), (1200, 440),
                (1200, 630), (0, 630)], fill=accent + (20,))

    # Painel de contraste para título, todo dentro da área central 1200x520.
    od.rounded_rectangle([58, 138, 1142, 496], radius=28,
                         fill=(0, 9, 24, 164), outline=(255, 255, 255, 28), width=1)

    # Pill do pilar, maior e legível em cards.
    f_pill = _font(BOLD, 28)
    label = pillar.upper()
    tw = od.textlength(label, font=f_pill)
    od.rounded_rectangle([80, 62, 80 + tw + 56, 116], radius=27,
                         fill=accent + (210,), outline=(255, 255, 255, 80), width=2)

    img = Image.alpha_composite(img, ov)
    d = ImageDraw.Draw(img)
    d.text((108, 73), label, font=f_pill, fill=WHITE)

    # Título: auto-fit em até 3 linhas curtas, dentro do crop 16:9 central.
    f_title, fs, lines, lh = _fit_title(d, title, 1000, 286)
    block_h = lh * len(lines)
    y = 318 - (block_h // 2)
    for ln in lines:
        d.text((80, y), ln, font=f_title, fill=WHITE,
               stroke_width=max(2, fs // 30), stroke_fill=(0, 10, 28))
        y += lh

    # Rodapé: dot + consorflow.com/blog, maior para thumb.
    d.ellipse([80, H - 92, 104, H - 68], fill=TEAL)
    f_foot = _font(BOLD, 30)
    x = 124
    for seg, col in [("consorflow", INK), (".com", accent), ("/blog", INK)]:
        d.text((x, H - 97), seg, font=f_foot, fill=col)
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
