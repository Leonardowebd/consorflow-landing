#!/usr/bin/env python3
"""
Gera imagens editoriais do blog via Gemini, com fallback externo no chamador.

Uso por import:
    from gerar_imagem_ia import gerar
    gerar("crm dashboard sales team", "Equipe olhando CRM", "img-1.jpg")

Requer opcionalmente:
    GEMINI_API_KEY
"""
import io
import os
import sys
from pathlib import Path


MODEL = "gemini-3.1-flash-image-preview"


def prompt_editorial(section_query, alt):
    return f"""
Fotografia editorial realista de negócios brasileira, horizontal 3:2.
Tema: {section_query}
Descrição desejada: {alt}

Direção visual:
- pessoas, ambientes ou objetos reais relacionados ao tema do artigo;
- estética limpa, profissional e moderna;
- tons navy e teal sutis, coerentes com uma marca SaaS B2B;
- luz natural ou corporativa suave;
- sem texto, sem legendas, sem números, sem gráficos com palavras;
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


def gerar(section_query, alt, out_path):
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


def main():
    if len(sys.argv) < 4:
        print('Uso: python3 gerar_imagem_ia.py "query" "alt" saida.jpg')
        return 1
    path = gerar(sys.argv[1], sys.argv[2], sys.argv[3])
    print(path or "sem imagem")
    return 0 if path else 1


if __name__ == "__main__":
    raise SystemExit(main())
