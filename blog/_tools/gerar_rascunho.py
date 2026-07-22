#!/usr/bin/env python3
"""Gera um rascunho SEO/AEO em posts/pending; nunca publica o artigo."""

import argparse
import datetime as dt
import html
import json
import os
import re
import tempfile
import urllib.request
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
QUEUE = TOOLS / "pautas.json"
PENDING = TOOLS / "posts" / "pending"
PUBLISHED = TOOLS / "posts"
SOURCE_LIMIT = 80_000


def extract_json(text):
    clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", str(text or "").strip(), flags=re.I)
    start, end = clean.find("{"), clean.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("O modelo não retornou um objeto JSON.")
    return json.loads(clean[start:end + 1])


def existing_slugs():
    files = list(PENDING.glob("*.json")) + [p for p in PUBLISHED.glob("*.json") if p.parent == PUBLISHED]
    return {p.stem for p in files}


def choose_topic(queue, used=None):
    used = used if used is not None else existing_slugs()
    for topic in queue.get("topics", []):
        if topic.get("slug") not in used and topic.get("enabled", True):
            return topic
    raise RuntimeError("Fila de pautas esgotada; adicione uma pauta revisada em pautas.json.")


def clean_source(raw):
    text = raw.decode("utf-8", errors="ignore")
    text = re.sub(r"<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return re.sub(r"\s+", " ", text).strip()[:SOURCE_LIMIT]


def fetch_sources(urls):
    extracts = []
    for url in urls:
        if not str(url).startswith("https://"):
            raise ValueError(f"Fonte rejeitada; use HTTPS: {url}")
        req = urllib.request.Request(url, headers={"User-Agent": "ConsorflowBlogBot/1.0"})
        with urllib.request.urlopen(req, timeout=25) as response:
            extracts.append({"url": url, "extract": clean_source(response.read(SOURCE_LIMIT * 2))})
    return extracts


def build_prompt(topic, sources, previous_errors=None):
    source_text = "\n\n".join(f"FONTE {item['url']}:\n{item['extract']}" for item in sources)
    correction = ""
    if previous_errors:
        correction = "\nA tentativa anterior falhou nestes critérios; corrija todos:\n- " + "\n- ".join(previous_errors)
    return f"""Escreva uma especificação JSON de artigo para o blog B2B da Consorflow.

Pauta: {topic['brief']}
Slug obrigatório: {topic['slug']}
Keyword principal: {topic['keyword']}
Pilar: {topic['pillar']}

Use somente fatos verificáveis nos extratos abaixo. Não invente números, datas, normas, fontes ou clientes. Toda afirmação temporal deve apontar para uma URL em sources. Consórcio não é investimento; nunca prometa contemplação, rentabilidade, retorno, lucro, prazo ou resultado garantido.

Entregue somente JSON com: slug, title (50-60 caracteres), meta_description (120-160), dek (80-200), keyword, pillar, date, read_min, image, sources (lista de URLs), sections e faq. Crie 4-6 sections; cada uma tem h2 em pergunta, answer com 30-60 palavras, paras com conteúdo aprofundado e opcionalmente h3/list/image_query/image_alt. Corpo total com pelo menos 1000 palavras, pelo menos um link interno HTML para /blog/ ou /, Consorflow citada pelo menos duas vezes, e última seção conectando o tema à Consorflow com CTA. Crie 3-5 FAQs com respostas de 30-60 palavras. Não use Markdown fora de strings HTML.

{source_text}{correction}"""


def call_gemini(prompt):
    from google import genai
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY ausente.")
    model = os.environ.get("BLOG_AI_MODEL", "gemini-2.5-flash")
    response = genai.Client(api_key=key).models.generate_content(model=model, contents=prompt)
    return extract_json(response.text)


def call_gateway(prompt):
    key = os.environ.get("AI_GATEWAY_API_KEY")
    model = os.environ.get("BLOG_AI_MODEL")
    if not key or not model:
        raise RuntimeError("AI_GATEWAY_API_KEY e BLOG_AI_MODEL são obrigatórias para provider=vercel.")
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"},
        "temperature": 0.35,
    }).encode()
    req = urllib.request.Request(
        "https://ai-gateway.vercel.sh/v1/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=90) as response:
        payload = json.loads(response.read())
    return extract_json(payload["choices"][0]["message"]["content"])


def hard_failures(post):
    from validar_post import validate
    _, _, failures = validate(post)
    return [f"{name}: {detail}" for name, _, _, detail in failures]


def normalize_post(post, topic):
    post["slug"] = topic["slug"]
    post["keyword"] = topic["keyword"]
    post["pillar"] = topic["pillar"]
    post["date"] = dt.date.today().isoformat()
    post["sources"] = topic.get("source_urls", [])
    post.setdefault("image", "/asset_dash.jpg")
    post.setdefault("read_min", 7)
    return post


def atomic_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        temp = Path(handle.name)
    temp.replace(path)


def readiness(provider, topic):
    required = ["GEMINI_API_KEY"] if provider == "gemini" else ["AI_GATEWAY_API_KEY", "BLOG_AI_MODEL"]
    return {
        "mode": "dry-run",
        "provider": provider,
        "topic": topic["slug"],
        "required_env": required,
        "missing_env": [name for name in required if not os.environ.get(name)],
        "will_fetch": topic.get("source_urls", []),
        "will_write": str(PENDING / f"{topic['slug']}.json"),
        "will_publish": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", default=str(QUEUE))
    parser.add_argument("--provider", choices=["gemini", "vercel"], default=os.environ.get("BLOG_AI_PROVIDER", "gemini"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fixture", help="JSON local para validar o fluxo sem IA nem rede")
    args = parser.parse_args()

    queue = json.loads(Path(args.queue).read_text(encoding="utf-8"))
    topic = choose_topic(queue)
    if args.dry_run:
        print(json.dumps(readiness(args.provider, topic), ensure_ascii=False, indent=2))
        return 0

    if args.fixture:
        post = normalize_post(json.loads(Path(args.fixture).read_text(encoding="utf-8")), topic)
    else:
        sources = fetch_sources(topic.get("source_urls", []))
        caller = call_gemini if args.provider == "gemini" else call_gateway
        errors = []
        for attempt in range(2):
            post = normalize_post(caller(build_prompt(topic, sources, errors)), topic)
            errors = hard_failures(post)
            if not errors:
                break
        if errors:
            raise RuntimeError("Rascunho reprovado no portão: " + " | ".join(errors))

    errors = hard_failures(post)
    if errors:
        raise RuntimeError("Rascunho reprovado no portão: " + " | ".join(errors))
    output = PENDING / f"{topic['slug']}.json"
    atomic_json(output, post)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
