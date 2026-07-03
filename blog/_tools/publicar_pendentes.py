#!/usr/bin/env python3
"""
Publica artigos aprovados no Telegram (poller).

Lê as respostas do Telegram (getUpdates), procura aprovações/recusas vindas do
seu chat e age: aprovado -> gera o post no site e dá git push (Vercel publica);
recusado -> descarta o rascunho. Não usa webhook nem arquivo de offset: confirma
os updates no próprio Telegram (cursor server-side).

Comandos aceitos (texto ou botão inline):
  /aprovar <slug>   ou  callback "aprovar:<slug>"
  /recusar <slug>   ou  callback "recusar:<slug>"

Requer: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
Uso (na raiz do repo clonado):
    python3 blog/_tools/publicar_pendentes.py
"""
import os, sys, json, subprocess, urllib.request, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]      # raiz do repo (site)
TOOLS = Path(__file__).resolve().parent
PENDING = TOOLS / "posts" / "pending"
PUBLISHED = TOOLS / "posts"
API = "https://api.telegram.org/bot{token}/{method}"


def tg(method, data=None):
    url = API.format(token=os.environ["TELEGRAM_BOT_TOKEN"], method=method)
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data or {}).encode())
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read())


def reply(text):
    tg("sendMessage", {"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": text})


def git(*args):
    subprocess.run(["git", "-C", str(ROOT), *args], check=True)


def aprovar(slug):
    print(f"[aprovar] slug={slug}", flush=True)
    spec = PENDING / f"{slug}.json"
    if not spec.exists():
        print(f"[aprovar] rascunho não encontrado: {spec}", flush=True)
        reply(f"⚠️ Rascunho não encontrado: {slug}")
        return
    dest = PUBLISHED / f"{slug}.json"
    print(f"[aprovar] movendo spec {spec} -> {dest}", flush=True)
    spec.replace(dest)  # move pending -> published
    print(f"[aprovar] gerando post com {dest}", flush=True)
    subprocess.run([sys.executable, str(TOOLS / "gerar_post.py"),
                    str(dest), "--site", str(ROOT)], check=True)
    print("[aprovar] git add/commit/push", flush=True)
    git("add", "-A")
    git("commit", "-m", f"blog: publica {slug} (aprovado via Telegram)")
    git("fetch", "origin", "main")
    git("rebase", "origin/main")
    git("push", "origin", "HEAD:main")
    reply(f"✅ Publicado: https://consorflow.com/blog/{slug}/")


def recusar(slug):
    print(f"[recusar] slug={slug}", flush=True)
    spec = PENDING / f"{slug}.json"
    if spec.exists():
        print(f"[recusar] removendo {spec}", flush=True)
        spec.unlink()
    reply(f"🗑 Rascunho descartado: {slug}")


def handle(cmd, slug):
    print(f"[decisão] cmd={cmd} slug={slug}", flush=True)
    if cmd == "aprovar":
        aprovar(slug)
    elif cmd == "recusar":
        recusar(slug)


def main():
    chat = str(os.environ["TELEGRAM_CHAT_ID"])
    res = tg("getUpdates", {"timeout": 0})
    updates = res.get("result", [])
    if not updates:
        print("sem novidades no Telegram")
        return 0

    last = 0
    for u in updates:
        last = max(last, u["update_id"])
        print(f"[update] update_id={u['update_id']}", flush=True)
        # botão inline
        if "callback_query" in u:
            cq = u["callback_query"]
            cb_chat = str(cq["message"]["chat"]["id"])
            print(f"[callback] chat_id={cb_chat} esperado={chat} data={cq.get('data','')}", flush=True)
            if cb_chat != chat:
                print("[callback] ignorado: chat_id diferente", flush=True)
                continue
            if ":" in cq.get("data", ""):
                cmd, slug = cq["data"].split(":", 1)
                if cmd == "aprovar":
                    tg("answerCallbackQuery", {
                        "callback_query_id": cq["id"],
                        "text": "⏳ Aprovação recebida — publicando...",
                        "show_alert": "false",
                    })
                    reply(f"⏳ Publicando {slug}...")
                else:
                    tg("answerCallbackQuery", {
                        "callback_query_id": cq["id"],
                        "text": "Recusa recebida.",
                        "show_alert": "false",
                    })
                handle(cmd, slug)
        # comando de texto
        msg = u.get("message", {})
        msg_chat = str(msg.get("chat", {}).get("id")) if msg else ""
        if msg:
            print(f"[message] chat_id={msg_chat} esperado={chat}", flush=True)
        if msg_chat == chat:
            txt = msg.get("text", "").strip()
            for cmd in ("aprovar", "recusar"):
                if txt.lower().startswith(f"/{cmd} "):
                    handle(cmd, txt.split(maxsplit=1)[1].strip())

    # confirma updates (avança o cursor server-side -> não reprocessa)
    tg("getUpdates", {"offset": last + 1, "timeout": 0})
    print(f"processados updates até {last}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
