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
import json, re, sys, argparse, html, os, shutil
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


def render_post(p):
    url = f"{BASE}/blog/{p['slug']}/"
    img = p.get("image", "/asset_dash.jpg")
    img_abs = img if img.startswith("http") else BASE + img

    faq_schema = [{
        "@type": "Question", "name": f["q"],
        "acceptedAnswer": {"@type": "Answer", "text": f["a"]}
    } for f in p.get("faq", [])]

    graph = [{
        "@type": "BlogPosting",
        "@id": url + "#post",
        "headline": p["title"], "description": p["meta_description"],
        "inLanguage": "pt-BR", "datePublished": p["date"], "dateModified": p["date"],
        "url": url, "image": img_abs,
        "author": {"@type": "Organization", "name": "Consorflow"},
        "publisher": {"@type": "Organization", "name": "Consorflow",
                      "logo": {"@type": "ImageObject", "url": f"{BASE}/asset_navlogo.svg"}},
        "mainEntityOfPage": url, "isPartOf": {"@id": f"{BASE}/blog/#blog"}
    }]
    if faq_schema:
        graph.append({"@type": "FAQPage", "@id": url + "#faq", "mainEntity": faq_schema})
    ld = json.dumps({"@context": "https://schema.org", "@graph": graph},
                    ensure_ascii=False, indent=2)

    body = []
    warns = []
    for s in p["sections"]:
        body.append(f'    <h2>{esc(s["h2"])}</h2>')
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
            if fig.get("credit"):
                body.append(f'      <figcaption>Foto: {esc(fig["credit"])} / {fig["origem"]}</figcaption>')
            body.append('    </figure>')
    body_html = "\n".join(body)

    faq_html = ""
    if p.get("faq"):
        items = "\n".join(
            f'      <details><summary>{esc(f["q"])}</summary><p>{esc(f["a"])}</p></details>'
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
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700&family=Funnel+Display:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/blog/blog.css?v=6">
<script type="application/ld+json">
{ld}
</script>
</head>
<body>
{NAV}
  <div class="wrap"><p class="crumbs"><a href="/">Início</a> › <a href="/blog/">Blog</a> › {esc(p["title"][:40])}</p></div>
  <article class="post">
    <header class="post-head">
      <div class="eyebrow">{esc(p["pillar"])}</div>
      <h1>{esc(p["title"])}</h1>
      <p class="dek">{esc(p["dek"])}</p>
      <div class="meta">Publicado em {p["date"]} · {p.get("read_min", 5)} min de leitura</div>
    </header>
    <img class="post-cover" src="{img}" alt="{esc(p["title"])}" loading="lazy" decoding="async" width="1200" height="630">
{body_html}
    <div class="cta-box">
      <h3>Sua operação está pronta para vender mais consórcio?</h3>
      <p>A Consorflow centraliza leads, WhatsApp, IA e funil para você responder rápido e não perder cota quente.</p>
      <a href="{WA}" target="_blank" rel="noopener">Solicitar uma demo</a>
    </div>{faq_html}
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


def attach_inline_image(section, slug, idx, post_dir, approved_dir=None):
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
    for i, s in enumerate(p.get("sections", []), 1):
        attach_inline_image(s, p["slug"], i, post_dir, approved_dir)
    if approved_dir:
        shutil.rmtree(approved_dir, ignore_errors=True)

    doc, url, warns = render_post(p)
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
