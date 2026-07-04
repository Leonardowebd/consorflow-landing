#!/usr/bin/env python3
"""
Gerador de posts do blog Consorflow.

Renderiza um post a partir de um JSON de especificação, no padrão visual do site
(blog.css), com schema BlogPosting + FAQPage e blocos de resposta GEO (30-60 palavras).
Atualiza automaticamente o grid de /blog/index.html e o sitemap.xml.

Uso:
    python3 gerar_post.py post.json [--site DIR]

DIR padrão = /Users/niina/Documents/IA/proto (source do consorflow.com no Vercel).

Schema do post.json:
{
  "slug": "consorcio-xyz",
  "title": "Título do post (50-60 chars ideal)",
  "meta_description": "120-160 chars",
  "dek": "Linha de apoio / subtítulo",
  "pillar": "Notícias do mundo | Mundo do consórcio | Tecnologia",
  "date": "2026-06-29",
  "read_min": 6,
  "image": "/asset_dash.jpg",
  "sections": [
    {"h2": "Pergunta em forma de H2?",
     "answer": "Resposta direta de 30-60 palavras (bloco GEO).",
     "paras": ["parágrafo 1", "parágrafo 2"],
     "h3": "Subtítulo opcional",
     "list": ["item 1", "item 2"]}
  ],
  "faq": [{"q": "Pergunta?", "a": "Resposta de 30-60 palavras."}]
}
"""
import json, re, sys, argparse, html, os, shutil, unicodedata
from pathlib import Path
from gerar_capa import render_capa
from buscar_imagem import buscar
from gerar_imagem_ia import gerar as gerar_ia

DEFAULT_SITE = "/Users/niina/Documents/IA/proto"
BASE = "https://consorflow.com"
WA = "https://wa.me/5577981454387?text=Ol%C3%A1%21+Gostaria+de+agendar+uma+demo+do+Consorflow."
TOOLS = Path(__file__).resolve().parent

NAV = f'''  <nav class="nav">
    <div class="navpill">
      <a class="logo" href="/"><img src="/asset_navlogo.svg" alt="Consorflow"></a>
      <div class="navlinks">
        <a href="/#solucoes">Soluções</a>
        <a href="/#funcionalidades">Plataforma</a>
        <a href="/blog/">Blog</a>
        <a href="/#planos">Planos</a>
        <a href="https://app.consorflow.com/" target="_blank" rel="noopener">Login</a>
      </div>
      <div class="navcta"><a class="navcta-face" href="{WA}" target="_blank" rel="noopener">Solicitar uma demo</a></div>
      <button class="navtoggle" id="navtoggle" aria-label="Abrir menu" aria-expanded="false" onclick="toggleMenu()"><span></span><span></span><span></span></button>
    </div>
    <div class="navmenu" id="navmenu">
      <a href="/#solucoes" onclick="closeMenu()">Soluções</a>
      <a href="/#funcionalidades" onclick="closeMenu()">Plataforma</a>
      <a href="/blog/" onclick="closeMenu()">Blog</a>
      <a href="/#planos" onclick="closeMenu()">Planos</a>
      <a href="https://app.consorflow.com/" target="_blank" rel="noopener" onclick="closeMenu()">Login</a>
      <a href="{WA}" class="navmenu-cta" onclick="closeMenu()" target="_blank" rel="noopener">Solicitar uma demo</a>
    </div>
  </nav>'''

FOOT = '''  <footer class="footer">
    <div class="footer-inner">
      <div class="footer-grid">
        <div class="footer-brand">
          <div class="flogo"><img src="/asset_footer_logo.svg" alt="Consorflow"></div>
          <div class="ftag">Tudo para operar vendas de consórcio em um só lugar.</div>
        </div>
        <div class="footer-col"><h4>Produto</h4><ul>
          <li><a href="/">Início</a></li><li><a href="/#funcionalidades">Funcionalidades</a></li><li><a href="/#planos">Planos</a></li><li><a href="/#faq">FAQ</a></li></ul></div>
        <div class="footer-col"><h4>Plataforma</h4><ul>
          <li><a href="/#funcionalidades">Leads</a></li><li><a href="/#funcionalidades">Funil de vendas</a></li><li><a href="/#funcionalidades">Campanhas</a></li><li><a href="/#funcionalidades">Relatórios</a></li></ul></div>
        <div class="footer-col"><h4>Legal</h4><ul>
          <li><a href="https://wa.me/5577981454387" target="_blank" rel="noopener">Contato</a></li><li><a href="/">Termos de uso</a></li><li><a href="/">Privacidade</a></li><li><a href="/">Cookies</a></li></ul></div>
      </div>
      <div class="footer-bottom"><span>© 2026 Consorflow. Todos os direitos reservados.</span></div>
    </div>
  </footer>'''

MENU_JS = '''  <script>
  function toggleMenu(){var m=document.getElementById('navmenu'),t=document.getElementById('navtoggle');var o=m.classList.toggle('open');t.classList.toggle('open',o);t.setAttribute('aria-expanded',o)}
  function closeMenu(){var m=document.getElementById('navmenu'),t=document.getElementById('navtoggle');if(m)m.classList.remove('open');if(t){t.classList.remove('open');t.setAttribute('aria-expanded','false')}}
  </script>'''


def esc(s):
    return html.escape(s, quote=True)


def wc(s):
    return len(re.findall(r"\b[\wÀ-ÿ-]+\b", s))


def text_only(s):
    s = html.unescape(str(s or ""))
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", s).strip()


def slugify(s):
    s = unicodedata.normalize("NFKD", text_only(s))
    s = s.encode("ascii", "ignore").decode("ascii").lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "secao"


def section_ids(sections):
    seen = {}
    for s in sections:
        base = slugify(s.get("h2", "secao"))
        seen[base] = seen.get(base, 0) + 1
        s["_id"] = base if seen[base] == 1 else f"{base}-{seen[base]}"


def first_answer(p):
    for s in p.get("sections", []):
        if s.get("answer"):
            return s["answer"]
    return p.get("dek", "")


def trim_words(text, max_words=60):
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]).rstrip(" ,;:") + "."


def fallback_tldr(p):
    base = text_only(first_answer(p))
    if wc(base) >= 40:
        return trim_words(base)
    parts = [base] if base else []
    for s in p.get("sections", []):
        for para in s.get("paras", []):
            clean = text_only(para)
            if not clean:
                continue
            sentence = re.split(r"(?<=[.!?])\s+", clean)[0]
            parts.append(sentence)
            candidate = trim_words(" ".join(parts))
            if wc(candidate) >= 40:
                return candidate
    return trim_words(" ".join(parts) or p.get("dek", ""))


def render_tldr(p):
    answer = text_only(p.get("tldr")) if p.get("tldr") else fallback_tldr(p)
    if not answer:
        return "", None
    n = wc(answer)
    warn = None
    if not 40 <= n <= 60:
        warn = f"TL;DR tem {n} palavras (ideal 40-60)"
    return f'''
    <aside class="tldr" aria-label="Resposta rápida">
      <div class="tldr-label">Resposta rápida</div>
      <p>{esc(answer)}</p>
    </aside>''', warn


def render_toc(sections):
    if len(sections) < 3:
        return ""
    items = "\n".join(
        f'        <li><a href="#{esc(s["_id"])}">{esc(s["h2"])}</a></li>'
        for s in sections
    )
    return f'''
    <nav class="toc" aria-labelledby="toc-title">
      <div id="toc-title" class="toc-title">Neste artigo</div>
      <ol>
{items}
      </ol>
    </nav>'''


def match_one(pattern, text, default=""):
    m = re.search(pattern, text, re.S)
    return text_only(m.group(1)) if m else default


def match_attr(pattern, text, default=""):
    m = re.search(pattern, text, re.S)
    return html.unescape(m.group(1)).strip() if m else default


def discover_posts(site):
    posts = []
    for path in sorted((site / "blog").glob("*/index.html")):
        slug = path.parent.name
        doc = path.read_text(encoding="utf-8")
        title = match_one(r"<h1>(.*?)</h1>", doc) or match_attr(r'<meta property="og:title" content="([^"]+)"', doc)
        if not title:
            continue
        pillar = match_one(r'<div class="eyebrow">(.*?)</div>', doc) or "Consorflow"
        pillar = pillar.split("·")[0].strip()
        posts.append({
            "slug": slug,
            "title": title,
            "pillar": pillar,
            "dek": match_one(r'<p class="dek">(.*?)</p>', doc),
            "date": match_attr(r'<meta property="article:published_time" content="([^"]+)"', doc),
            "img": match_attr(r'<img class="post-cover" src="([^"]+)"', doc) or f"/blog/{slug}/capa.png",
        })
    return posts


def render_related(site, p):
    posts = [r for r in discover_posts(site) if r["slug"] != p["slug"]]
    same = sorted([r for r in posts if r["pillar"] == p.get("pillar")], key=lambda r: r["date"], reverse=True)
    other = sorted([r for r in posts if r["pillar"] != p.get("pillar")], key=lambda r: r["date"], reverse=True)
    related = (same + other)[:3]
    if not related:
        return ""
    cards = "\n".join(f'''
        <a class="related-card" href="/blog/{r["slug"]}/">
          <span class="tag">{esc(r["pillar"])}</span>
          <h3>{esc(r["title"])}</h3>
          <p>{esc(r["dek"])}</p>
        </a>''' for r in related)
    return f'''
    <section class="related" aria-labelledby="related-title">
      <h2 id="related-title">Leia também</h2>
      <div class="related-grid">
{cards}
      </div>
    </section>'''


def render_author_box():
    return '''
    <aside class="author-box">
      <img src="/asset_navlogo.svg" alt="Consorflow" width="42" height="42" loading="lazy" decoding="async">
      <div>
        <div class="author-name">Equipe Consorflow</div>
        <p>Especialistas em gestão comercial de consórcio — plataforma usada por administradoras e corretoras.</p>
      </div>
    </aside>'''


def render_post(p, site):
    section_ids(p.get("sections", []))
    url = f"{BASE}/blog/{p['slug']}/"
    img = p.get("image", "/asset_dash.jpg")
    img_abs = img if img.startswith("http") else BASE + img
    updated = p.get("updated") or p["date"]

    faq_schema = [{
        "@type": "Question", "name": f["q"],
        "acceptedAnswer": {"@type": "Answer", "text": f["a"]}
    } for f in p.get("faq", [])]

    graph = [{
        "@type": "BlogPosting",
        "@id": url + "#post",
        "headline": p["title"], "description": p["meta_description"],
        "inLanguage": "pt-BR", "datePublished": p["date"], "dateModified": updated,
        "url": url, "image": img_abs,
        "author": {"@type": "Organization", "name": "Consorflow"},
        "publisher": {"@type": "Organization", "name": "Consorflow",
                      "logo": {"@type": "ImageObject", "url": f"{BASE}/asset_navlogo.svg"}},
        "speakable": {"@type": "SpeakableSpecification", "cssSelector": [".answer"]},
        "mainEntityOfPage": url, "isPartOf": {"@id": f"{BASE}/blog/#blog"}
    }, {
        "@type": "BreadcrumbList",
        "@id": url + "#breadcrumb",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Início", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Blog", "item": BASE + "/blog/"},
            {"@type": "ListItem", "position": 3, "name": p["title"], "item": url}
        ]
    }]
    if faq_schema:
        graph.append({"@type": "FAQPage", "@id": url + "#faq", "mainEntity": faq_schema})
    ld = json.dumps({"@context": "https://schema.org", "@graph": graph},
                    ensure_ascii=False, indent=2)

    tldr_html, tldr_warn = render_tldr(p)
    toc_html = render_toc(p.get("sections", []))
    related_html = render_related(site, p)

    body = []
    warns = []
    if tldr_warn:
        warns.append(tldr_warn)
    for s in p["sections"]:
        body.append(f'    <h2 id="{esc(s["_id"])}">{esc(s["h2"])}</h2>')
        if s.get("answer"):
            n = wc(s["answer"])
            if not 30 <= n <= 60:
                warns.append(f'bloco GEO "{s["h2"][:40]}" tem {n} palavras (ideal 30-60)')
            body.append(f'    <div class="answer">{esc(s["answer"])}</div>')
        for para in s.get("paras", []):
            body.append(f'    <p>{para}</p>')
        if s.get("h3"):
            body.append(f'    <h3>{esc(s["h3"])}</h3>')
        if s.get("list"):
            body.append('    <ul>')
            body += [f'      <li>{li}</li>' for li in s["list"]]
            body.append('    </ul>')
        if s.get("_img"):
            fig = s["_img"]
            body.append(f'    <figure class="post-fig"><img src="{fig["src"]}" alt="{esc(fig["alt"])}" loading="lazy" decoding="async" width="1200" height="800">')
            caption = figure_caption(fig)
            if caption:
                body.append(f'      <figcaption>{esc(caption)}</figcaption>')
            body.append('    </figure>')
    body_html = "\n".join(body)

    faq_html = ""
    if p.get("faq"):
        items = "\n".join(
            f'      <details id="faq-{slugify(f["q"])}"><summary>{esc(f["q"])}</summary><p>{esc(f["a"])}</p></details>'
            for f in p["faq"])
        faq_html = f'''
    <section class="faq">
      <h2>Perguntas frequentes</h2>
{items}
    </section>'''

    doc = f'''<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<!-- Google Tag Manager -->
<script>(function(w,d,s,l,i){{w[l]=w[l]||[];w[l].push({{'gtm.start':new Date().getTime(),event:'gtm.js'}});var f=d.getElementsByTagName(s)[0],j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src='https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);}})(window,document,'script','dataLayer','GTM-PGTFC8HQ');</script>
<!-- End Google Tag Manager -->
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(p["title"])} | Consorflow</title>
<meta name="description" content="{esc(p["meta_description"])}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index,follow,max-image-preview:large">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Consorflow">
<meta property="og:title" content="{esc(p["title"])}">
<meta property="og:description" content="{esc(p["meta_description"])}">
<meta property="og:url" content="{url}">
<meta property="og:locale" content="pt_BR">
<meta property="og:image" content="{img_abs}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="{img_abs}">
<meta property="article:published_time" content="{p["date"]}">
<meta property="article:modified_time" content="{updated}">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700&family=Funnel+Display:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/blog/blog.css?v=8">
<script type="application/ld+json">
{ld}
</script>
</head>
<body>
<!-- Google Tag Manager (noscript) -->
<noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-PGTFC8HQ" height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
<!-- End Google Tag Manager (noscript) -->
{NAV}
  <div class="wrap"><p class="crumbs"><a href="/">Início</a> › <a href="/blog/">Blog</a> › {esc(p["title"][:40])}</p></div>
  <article class="post">
    <header class="post-head">
      <div class="eyebrow">{esc(p["pillar"])}</div>
      <h1>{esc(p["title"])}</h1>
      <p class="dek">{esc(p["dek"])}</p>
      <div class="meta">Publicado em {p["date"]} · Atualizado em {updated} · {p.get("read_min", 5)} min de leitura</div>
    </header>
    <img class="post-cover" src="{img}" alt="{esc(p["title"])}" loading="lazy" decoding="async" width="1200" height="630">
{tldr_html}
{toc_html}
{body_html}
{faq_html}
{render_author_box()}
    <div class="cta-box">
      <h3>Sua operação está pronta para vender mais consórcio?</h3>
      <p>A Consorflow centraliza leads, WhatsApp, IA e funil para você responder rápido e não perder cota quente.</p>
      <a href="{WA}" target="_blank" rel="noopener">Solicitar uma demo</a>
    </div>
{related_html}
  </article>
{FOOT}
{MENU_JS}
</body>
</html>
'''
    return doc, url, warns


def card_html(p):
    img = p.get("image", "/asset_dash.jpg")
    return f'''
      <a class="card" href="/blog/{p['slug']}/">
        <div class="thumb"><img src="{img}" alt="{esc(p['title'])}" loading="lazy" decoding="async" width="1200" height="630"></div>
        <div class="body">
          <span class="tag">{esc(p['pillar'])}</span>
          <h2>{esc(p['title'])}</h2>
          <p>{esc(p['dek'])}</p>
          <div class="meta">{p['date']} · {p.get('read_min',5)} min de leitura</div>
        </div>
      </a>
'''


def update_index(site, p):
    idx = site / "blog" / "index.html"
    t = idx.read_text(encoding="utf-8")
    marker = "<!-- BLOG_GRID_START -->\n    <div class=\"grid\">"
    if f'/blog/{p["slug"]}/' in t:
        # já existe: não duplica
        return
    t = t.replace(marker, marker + card_html(p), 1)
    idx.write_text(t, encoding="utf-8")


def update_sitemap(site, url, date):
    sm = site / "sitemap.xml"
    t = sm.read_text(encoding="utf-8")
    if url in t:
        return
    entry = (f"  <url>\n    <loc>{url}</loc>\n    <lastmod>{date}</lastmod>\n"
             f"    <changefreq>monthly</changefreq>\n    <priority>0.7</priority>\n  </url>\n")
    t = t.replace("</urlset>", entry + "</urlset>")
    sm.write_text(t, encoding="utf-8")


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


def approved_assets_dir(spec_path, slug):
    candidates = [
        Path(spec_path).resolve().parent / "assets" / slug,
        TOOLS / "posts" / "pending" / "assets" / slug,
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def existing_figure_meta(post_dir, fn, fallback_alt):
    path = post_dir / "index.html"
    if not path.exists():
        return None
    doc = path.read_text(encoding="utf-8")
    m = re.search(
        rf'<figure class="post-fig"><img[^>]+src="[^"]*/{re.escape(fn)}"[^>]*>(?:\s*<figcaption>(.*?)</figcaption>)?',
        doc,
        re.S,
    )
    if not m:
        return None
    caption = text_only(m.group(1)) if m.group(1) else ""
    meta = {"alt": fallback_alt, "credit": "", "origem": "", "caption": caption}
    if caption.startswith("Foto: ") and " / " in caption:
        credit, origem = caption[6:].rsplit(" / ", 1)
        meta.update({"credit": credit.strip(), "origem": origem.strip()})
    return meta


def figure_caption(fig):
    if fig.get("caption"):
        return fig["caption"]
    origem = fig.get("origem", "")
    credit = fig.get("credit", "")
    if origem == "Pexels" and credit:
        return f"Foto: {credit} / Pexels"
    if origem == "Gemini":
        return f"Imagem gerada por IA: {fig.get('alt', '')}"
    return fig.get("alt", "")


def attach_inline_image(section, slug, idx, post_dir, approved_dir=None, generate_missing=True):
    query = section.get("image_query")
    if not query:
        return None

    fn = f"img-{idx}.jpg"
    target = post_dir / fn
    alt = section.get("image_alt") or query
    meta = None

    if approved_dir:
        asset = approved_dir / fn
        if asset.exists():
            asset.replace(target)
            meta = read_json(approved_dir / f"img-{idx}.json") or {
                "alt": alt,
                "credit": "Consorflow IA",
                "origem": "Gemini",
            }
            print(f"  imagem inline §{idx}: reusada do preview aprovado -> {fn}")

    if not meta and target.exists():
        meta = existing_figure_meta(post_dir, fn, alt) or {
            "alt": alt,
            "credit": "",
            "origem": "",
        }
        print(f"  imagem inline §{idx}: mantida imagem publicada -> {fn}")

    if not meta and not generate_missing:
        print(f"  (sem imagem inline §{idx}: '{query}' — preservando post publicado sem gerar nova imagem)")
        return None

    if not meta and os.environ.get("GEMINI_API_KEY"):
        generated = gerar_ia(query, alt, str(target))
        if generated:
            meta = {
                "alt": alt,
                "credit": "Consorflow IA",
                "origem": "Gemini",
            }
            print(f"  imagem inline §{idx}: Gemini -> {fn}")

    if not meta:
        info = buscar(query, str(target))
        if info:
            meta = {
                "alt": alt,
                "credit": info.get("credit", ""),
                "origem": info.get("origem", "Pexels"),
            }
            print(f"  imagem inline §{idx}: {query} -> {meta['credit']}/{meta['origem']}")

    if meta:
        section["_img"] = {
            "src": f"/blog/{slug}/{fn}",
            "alt": meta.get("alt") or alt,
            "credit": meta.get("credit", ""),
            "origem": meta.get("origem", ""),
        }
        return section["_img"]

    print(f"  (sem imagem inline §{idx}: '{query}' — sem Gemini/Pexels ou sem resultado)")
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", help="arquivo post.json")
    ap.add_argument("--site", default=DEFAULT_SITE)
    ap.add_argument("--force", action="store_true",
                    help="publica mesmo reprovando no portão de qualidade")
    ap.add_argument("--no-gate", action="store_true",
                    help="pula o portão de curadoria (não recomendado)")
    args = ap.parse_args()

    site = Path(args.site)
    p = json.loads(Path(args.spec).read_text(encoding="utf-8"))

    # ── Portão de curadoria/qualidade (SEO + GEO + compliance) ──
    if not args.no_gate:
        from validar_post import report
        score, hard_fail = report(p)
        if hard_fail and not args.force:
            print("  ⛔ Post REPROVADO no portão de qualidade — NÃO publicar.")
            print("     Ajuste a spec e rode de novo (ou use --force para sobrepor).")
            return 1

    post_dir = site / "blog" / p["slug"]
    post_dir_existed = post_dir.exists()
    post_dir.mkdir(parents=True, exist_ok=True)

    # Capa editorial gerada (identidade Consorflow) — vira a imagem do post,
    # a menos que o spec defina "image" explicitamente.
    if not p.get("image"):
        render_capa(p["title"], p.get("pillar", "Consorflow"),
                    str(post_dir / "capa.png"))
        p["image"] = f"/blog/{p['slug']}/capa.png"

    # Imagens inline: se houver preview aprovado, reusa exatamente aqueles arquivos.
    # Sem preview aprovado: tenta Gemini; se falhar, tenta Pexels; se falhar, segue sem figura.
    approved_dir = approved_assets_dir(args.spec, p["slug"])
    is_existing_published = post_dir_existed and not approved_dir and Path(args.spec).resolve().parent == TOOLS / "posts"
    for i, s in enumerate(p.get("sections", []), 1):
        attach_inline_image(s, p["slug"], i, post_dir, approved_dir,
                            generate_missing=not is_existing_published)
    if approved_dir:
        shutil.rmtree(approved_dir, ignore_errors=True)

    doc, url, warns = render_post(p, site)
    (post_dir / "index.html").write_text(doc, encoding="utf-8")
    update_index(site, p)
    update_sitemap(site, url, p["date"])

    print(f"OK post gerado: {url}")
    print(f"  arquivo: {post_dir/'index.html'}")
    for w in warns:
        print(f"  AVISO GEO: {w}")
    print("Deploy: cd", args.site, "&& vercel deploy --prod --yes")


if __name__ == "__main__":
    raise SystemExit(main())
