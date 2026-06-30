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
            body += (f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{fn}\"\r\n"
                     f"Content-Type: image/png\r\n\r\n").encode()
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


def main():
    spec = sys.argv[1]
    p = json.loads(Path(spec).read_text(encoding="utf-8"))
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

    # corpo
    send_chunks(chat, article_text(p))

    # botões
    kb = {"inline_keyboard": [[
        {"text": "✅ Aprovar e publicar", "callback_data": f"aprovar:{slug}"},
        {"text": "❌ Recusar", "callback_data": f"recusar:{slug}"},
    ]]}
    _post("sendMessage", {
        "chat_id": chat,
        "text": f"Publicar “{p['title']}”?\n(ou responda: /aprovar {slug}  |  /recusar {slug})",
        "reply_markup": json.dumps(kb),
    })
    print(f"OK enviado ao Telegram: {slug} (nota {score}/100, {status})")


if __name__ == "__main__":
    raise SystemExit(main())
