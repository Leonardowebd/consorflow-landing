#!/usr/bin/env python3
"""
Gera imagens editoriais do blog via IA, com fallback externo no chamador.

Uso por import:
    from gerar_imagem_ia import gerar
    gerar("crm dashboard sales team", "Equipe olhando CRM", "img-1.jpg")

Requer opcionalmente para a primeira opção:
    GEMINI_API_KEY
"""
import io
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


MODEL = "gemini-3.1-flash-image-preview"
POLLINATIONS = "https://image.pollinations.ai/prompt/{prompt}?width=1600&height=1067&nologo=true&enhance=true&model={model}"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


def prompt_editorial(section_query, alt):
    return f"""
Fotografia editorial realista de negócios brasileira, horizontal 3:2.
Tema: {section_query}
Descrição desejada: {alt}

Direção visual:
- professional editorial photography, 85mm lens, natural lighting, high detail, photorealistic;
- pessoas, ambientes ou objetos reais relacionados ao tema do artigo;
- estética limpa, profissional e moderna;
- tons navy e teal sutis, coerentes com uma marca SaaS B2B;
- luz natural ou corporativa suave;
- sem texto, sem legendas, sem números, sem gráficos com palavras;
- no text, no watermark, no logos;
- sem logos, marcas, telas legíveis ou identidade de terceiros;
- imagem útil para ilustrar artigo de blog sobre consórcio, vendas, CRM e gestão comercial.
""".strip()


def _save_image(data, out_path):
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.save(out, "JPEG", quality=88, optimize=True)
    except Exception:
        out.write_bytes(data)
    return str(out)


def _has_image_magic(data):
    return data.startswith(b"\xff\xd8\xff") or data.startswith(b"\x89PNG\r\n\x1a\n")


def _is_image_response(content_type, data):
    return (content_type or "").lower().startswith("image/") or _has_image_magic(data)


def _gerar_gemini(section_query, alt, out_path):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("aviso: google-genai não instalado; pulando Gemini", file=sys.stderr)
        return None

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=MODEL,
            contents=[prompt_editorial(section_query, alt)],
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"],
            ),
        )

        for candidate in response.candidates or []:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", []) or []:
                inline = getattr(part, "inline_data", None)
                if inline and getattr(inline, "data", None):
                    return _save_image(inline.data, out_path)
        print(f"aviso: Gemini não retornou imagem ({section_query})", file=sys.stderr)
        return None
    except Exception as e:
        print(f"aviso: Gemini falhou ({section_query}): {e}", file=sys.stderr)
        return None


def _gerar_pollinations(section_query, alt, out_path):
    prompt = urllib.parse.quote(prompt_editorial(section_query, alt), safe="")
    attempts = [
        ("flux-realism", 5),
        ("flux", 15),
        ("flux", 30),
    ]

    for attempt, (model, delay) in enumerate(attempts, start=1):
        try:
            url = POLLINATIONS.format(prompt=prompt, model=model)
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"})
            with urllib.request.urlopen(req, timeout=90) as r:
                data = r.read()
                content_type = r.headers.get("Content-Type", "")
            if data and _is_image_response(content_type, data):
                return _save_image(data, out_path)
            print(
                f"aviso: Pollinations retornou resposta não-imagem "
                f"(tentativa {attempt}, model={model}, content-type={content_type or 'vazio'})",
                file=sys.stderr,
            )
        except urllib.error.HTTPError as e:
            body = e.read(400)
            print(
                f"aviso: Pollinations HTTP {e.code} "
                f"(tentativa {attempt}, model={model}): {body[:160]!r}",
                file=sys.stderr,
            )
        except Exception as e:
            print(f"aviso: Pollinations falhou (tentativa {attempt}, model={model}): {e}", file=sys.stderr)

        if attempt < len(attempts):
            time.sleep(delay)

    return None


def gerar(section_query, alt, out_path):
    return (
        _gerar_gemini(section_query, alt, out_path)
        or _gerar_pollinations(section_query, alt, out_path)
    )


def main():
    if len(sys.argv) < 4:
        print('Uso: python3 gerar_imagem_ia.py "query" "alt" saida.jpg')
        return 1
    path = gerar(sys.argv[1], sys.argv[2], sys.argv[3])
    print(path or "sem imagem")
    return 0 if path else 1


if __name__ == "__main__":
    raise SystemExit(main())
