#!/usr/bin/env python3
"""
Envia um rascunho de artigo para aprovação no Telegram.

Fluxo: o redator gera a spec em posts/pending/<slug>.json, roda o portão
(validar_post) e chama este script. O dono recebe no Telegram a capa, o resumo,
a nota de qualidade, o corpo do artigo e botões Aprovar/Recusar.

Requer as variáveis de ambiente:
  TELEGRAM_BOT_TOKEN  — token do bot (BotFather)
  TELEGRAM_CHAT_ID    — chat id do destinatário (você)

Uso:
    python3 enviar_telegram.py posts/pending/<slug>.json
"""
import os, sys, json, urllib.request, urllib.parse
from pathlib import Path
from validar_post import validate, all_text
from gerar_capa import render_capa
from buscar_imagem import buscar
from gerar_imagem_ia import gerar as gerar_ia

API = "https://api.telegram.org/bot{token}/{method}"


def _post(method, data=None, files=None):
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    url = API.format(token=token, method=method)
    if files:  # multipart (sendPhoto)
        import mimetypes, uuid
        boundary = uuid.uuid4().hex
        body = b""
        for k, v in (data or {}).items():
            body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n").encode()
        for k, path in files.items():
            fn = os.path.basename(path)
            content_type = mimetypes.guess_type(path)[0] or "application/octet-stream"
            body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{fn}\"\r\n"
                     f"Content-Type: {content_type}\r\n\r\n").encode()
            body += open(path, "rb").read() + b"\r\n"
        body += f"--{boundary}--\r\n".encode()
        req = urllib.request.Request(url, data=body)
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    else:
        req = urllib.request.Request(
            url, data=urllib.parse.urlencode(data or {}).encode())
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def article_text(p):
    """Versão legível (texto) do artigo para revisão no Telegram."""
    out = [f"📰 {p['title']}\n", f"🏷 {p.get('pillar','')}  ·  {p.get('read_min',5)} min", ""]
    out.append(p.get("dek", ""))
    for s in p.get("sections", []):
        out.append(f"\n— {s['h2']}")
        if s.get("answer"):
            out.append(s["answer"])
        for para in s.get("paras", []):
            out.append(__import__("re").sub(r"<[^>]+>", "", para))
        for li in s.get("list", []):
            out.append(f"• {li}")
    if p.get("faq"):
        out.append("\nPerguntas frequentes:")
        for f in p["faq"]:
            out.append(f"❓ {f['q']}\n{f['a']}")
    return "\n".join(out)


def send_chunks(chat, text):
    for i in range(0, len(text), 3800):
        _post("sendMessage", {"chat_id": chat, "text": text[i:i + 3800]})


def _write_meta(path, meta):
    Path(path).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_meta(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


def _caption(idx, meta):
    alt = meta.get("alt", "")
    credit = meta.get("credit", "")
    origem = meta.get("origem", "")
    if origem == "Pexels":
        return f"Imagem §{idx}: {alt} — Foto: {credit}/Pexels"
    return f"Imagem §{idx}: {alt} — Imagem gerada por IA"


def ensure_section_image_asset(section, slug, idx, assets_dir):
    query = section.get("image_query")
    if not query:
        return None
    assets_dir.mkdir(parents=True, exist_ok=True)
    out = assets_dir / f"img-{idx}.jpg"
    meta_path = assets_dir / f"img-{idx}.json"
    alt = section.get("image_alt") or query

    if out.exists():
        meta = _read_meta(meta_path) or {
            "path": str(out),
            "alt": alt,
            "credit": "Consorflow IA",
            "origem": "Pollinations",
        }
        meta["path"] = str(out)
        return meta

    if os.environ.get("PEXELS_API_KEY"):
        info = buscar(query, str(out), alt=alt)
        if info:
            meta = {
                "path": info["path"],
                "alt": alt,
                "credit": info.get("credit", ""),
                "origem": "Pexels",
                "query": info.get("query") or query,
            }
            _write_meta(meta_path, meta)
            return meta

    generated = gerar_ia(query, alt, str(out))
    if generated:
        meta = {
            "path": generated,
            "alt": alt,
            "credit": "Consorflow IA",
            "origem": "Pollinations",
        }
        _write_meta(meta_path, meta)
        return meta

    return None


def send_section_images(chat, p, spec_path):
    slug = p["slug"]
    assets_dir = spec_path.parent / "assets" / slug
    for idx, section in enumerate(p.get("sections", []), start=1):
        try:
            meta = ensure_section_image_asset(section, slug, idx, assets_dir)
            if not meta:
                continue
            _post("sendPhoto", {"chat_id": chat, "caption": _caption(idx, meta)},
                  files={"photo": meta["path"]})
        except Exception as e:
            print(f"aviso: preview de imagem falhou (§{idx}): {e}", file=sys.stderr)


def main():
    spec_path = Path(sys.argv[1])
    p = json.loads(spec_path.read_text(encoding="utf-8"))
    chat = os.environ["TELEGRAM_CHAT_ID"]
    slug = p["slug"]

    checks, score, hard_fail = validate(p)
    status = "✅ PASS" if not hard_fail else f"❌ FAIL ({len(hard_fail)} bloqueios)"
    body_wc = len(all_text(p).split())

    # capa
    cover = f"/tmp/capa_{slug}.png"
    render_capa(p["title"], p.get("pillar", "Consorflow"), cover)
    caption = (f"📝 Rascunho do dia\n\n*{p['title']}*\n\n"
               f"Pilar: {p.get('pillar','')}\nNota SEO/qualidade: *{score}/100*  {status}\n"
               f"~{body_wc} palavras\n\n_Revise abaixo e aprove para publicar._")
    _post("sendPhoto", {"chat_id": chat, "caption": caption, "parse_mode": "Markdown"},
          files={"photo": cover})

    # previews de imagens inline que serão usadas após aprovação
    send_section_images(chat, p, spec_path)

    # corpo
    send_chunks(chat, article_text(p))

    # botões
    kb = {"inline_keyboard": [[
        {"text": "✅ Aprovar e publicar", "callback_data": f"aprovar:{slug}"},
        {"text": "❌ Recusar", "callback_data": f"recusar:{slug}"},
    ]]}
    _post("sendMessage", {
        "chat_id": chat,
        "text": (f"Publicar “{p['title']}”?\n"
                 f"(ou responda: /aprovar {slug}  |  /recusar {slug})\n"
                 "Após aprovar, a publicação sai na próxima janela de 10 minutos (UTC)."),
        "reply_markup": json.dumps(kb),
    })
    print(f"OK enviado ao Telegram: {slug} (nota {score}/100, {status})")


if __name__ == "__main__":
    raise SystemExit(main())
