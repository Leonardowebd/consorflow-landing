#!/usr/bin/env python3
"""
Portão de qualidade/curadoria do blog Consorflow.

Avalia uma spec de post (post.json) contra critérios objetivos de SEO, GEO/AEO,
estrutura e compliance. Imprime um relatório com nota /100 e PASS/FAIL.
Sai com código != 0 se houver qualquer FALHA (regra dura) — o fluxo de
publicação só deve seguir quando o post passa.

Uso:
    python3 validar_post.py post.json
    python3 validar_post.py post.json --json   # saída estruturada
"""
import json, re, sys, argparse

# ── Compliance Consorflow: promessas proibidas (regra dura = bloqueia) ──
# Consórcio NÃO é investimento; nunca prometer contemplação, rentabilidade
# ou resultado garantido.
BANNED = [
    r"contempla\w*\s+garantid", r"garant\w+\s+(a|de|sua)\s+contempla",
    r"rentabilidade", r"rendimento garantid", r"retorno garantid",
    r"lucro garantid", r"investimento garantid", r"ganho garantid",
    r"sem risco", r"risco zero", r"dinheiro f[aá]cil", r"enriquec",
    r"\b(vai|ir[aá]|ser[aá]|sera)\s+(ser\s+)?contemplad",
    r"garantimos\s+(o|a|que)",
]

WORD_RE = re.compile(r"\b[\wÀ-ÿ-]+\b", re.UNICODE)


def wc(s):
    return len(WORD_RE.findall(s or ""))


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s or "")


def all_text(p):
    parts = [p.get("title", ""), p.get("meta_description", ""), p.get("dek", "")]
    for s in p.get("sections", []):
        parts += [s.get("h2", ""), s.get("answer", "")]
        parts += s.get("paras", [])
        parts += s.get("list", [])
        parts.append(s.get("h3", ""))
    for f in p.get("faq", []):
        parts += [f.get("q", ""), f.get("a", "")]
    return strip_tags(" ".join(parts))


def primary_keyword(p):
    if p.get("keyword"):
        return p["keyword"].lower()
    # deriva do slug: remove stopwords curtas
    stop = {"de", "do", "da", "e", "o", "a", "em", "no", "na", "que", "com", "sem", "para"}
    toks = [t for t in p.get("slug", "").split("-") if t not in stop]
    return " ".join(toks[:3]).lower()


def validate(p):
    checks = []  # (nome, ok, hard, detalhe)  hard=True => falha bloqueia

    def chk(name, ok, hard, detail=""):
        checks.append((name, bool(ok), hard, detail))

    title = p.get("title", "")
    meta = p.get("meta_description", "")
    dek = p.get("dek", "")
    slug = p.get("slug", "")
    sections = p.get("sections", [])
    faq = p.get("faq", [])
    text = all_text(p)
    body_wc = sum(wc(" ".join(s.get("paras", []) + s.get("list", []) + [s.get("answer", "")]))
                  for s in sections)
    kw = primary_keyword(p)
    low = text.lower()

    # ── SEO técnico ──
    chk("Título 50–60 chars", 50 <= len(title) <= 60, False, f"{len(title)} chars")
    chk("Título ≤ 65 chars (corte do Google)", len(title) <= 65, True, f"{len(title)} chars")
    chk("Meta description 120–160 chars", 120 <= len(meta) <= 160, True, f"{len(meta)} chars")
    chk("Slug válido (kebab-case, ≤60)", bool(re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug)) and len(slug) <= 60, True, slug)
    chk("Dek/subtítulo presente (80–200)", dek and 80 <= len(dek) <= 200, False, f"{len(dek)} chars")

    # ── Palavra-chave (relevância) ──
    chk(f"Keyword '{kw}' no título", kw and kw.split()[0] in title.lower(), False)
    chk(f"Keyword '{kw}' na meta", kw and kw.split()[0] in meta.lower(), False)
    chk(f"Keyword '{kw}' no 1º parágrafo", kw and sections and kw.split()[0] in all_text({"sections": sections[:1]}).lower(), False)
    # anti keyword-stuffing
    if kw:
        tok = kw.split()[0]
        n_kw = len(re.findall(r"\b" + re.escape(tok) + r"\b", low))
        dens = n_kw / max(wc(text), 1)
        chk("Sem keyword stuffing (densidade < 4%)", dens < 0.04, True, f"{dens*100:.1f}% ({n_kw}x)")

    # ── Estrutura / GEO-AEO ──
    chk("≥ 3 seções (H2)", len(sections) >= 3, True, f"{len(sections)} seções")
    q_h2 = sum(1 for s in sections if s.get("h2", "").rstrip().endswith("?"))
    chk("≥ 50% dos H2 em forma de pergunta", sections and q_h2 / len(sections) >= 0.5, False, f"{q_h2}/{len(sections)}")
    bad_ans = [s["h2"][:30] for s in sections if s.get("answer") and not (30 <= wc(s["answer"]) <= 60)]
    chk("Blocos-resposta GEO 30–60 palavras", not bad_ans, True, "; ".join(bad_ans) if bad_ans else "ok")
    n_ans = sum(1 for s in sections if s.get("answer"))
    chk("≥ 2 blocos-resposta GEO", n_ans >= 2, False, f"{n_ans} blocos")

    # ── Profundidade / conteúdo ──
    chk("Corpo ≥ 700 palavras", body_wc >= 700, True, f"{body_wc} palavras")
    chk("Corpo ≥ 1000 palavras (ideal)", body_wc >= 1000, False, f"{body_wc} palavras")

    # ── Links ──
    body_html = " ".join(" ".join(s.get("paras", [])) for s in sections)
    chk("≥ 1 link interno (href=\"/...\")", len(re.findall(r'href="/', body_html)) >= 1, False)

    # ── FAQ / schema ──
    chk("FAQ com ≥ 3 perguntas", len(faq) >= 3, True, f"{len(faq)} perguntas")
    bad_faq = [f["q"][:30] for f in faq if not (30 <= wc(f.get("a", "")) <= 60)]
    chk("Respostas de FAQ 30–60 palavras", not bad_faq, False, "; ".join(bad_faq) if bad_faq else "ok")

    # ── Imagem ──
    chk("Pilar definido (cor da capa)", bool(p.get("pillar")), False, p.get("pillar", ""))
    n_inline = sum(1 for s in sections if s.get("image_query"))
    chk("≥ 2 imagens inline (banco de imagens)", n_inline >= 2, False, f"{n_inline} marcadas")

    # ── Compliance (regra dura) ──
    hits = sorted({m.group(0) for pat in BANNED for m in re.finditer(pat, low)})
    chk("Compliance: sem promessa de contemplação/rentabilidade", not hits, True,
        "ENCONTRADO: " + ", ".join(hits) if hits else "ok")

    # ── Nota ──
    total = len(checks)
    passed = sum(1 for _, ok, _, _ in checks if ok)
    score = round(100 * passed / total)
    hard_fail = [c for c in checks if c[2] and not c[1]]
    return checks, score, hard_fail


def report(p):
    checks, score, hard_fail = validate(p)
    print(f"\n  Curadoria — {p.get('slug','(sem slug)')}")
    print("  " + "─" * 60)
    for name, ok, hard, detail in checks:
        mark = "✓" if ok else ("✗" if hard else "!")
        tag = "" if ok else ("  [BLOQUEIA]" if hard else "  [melhorar]")
        d = f"  — {detail}" if detail else ""
        print(f"  {mark} {name}{d}{tag}")
    print("  " + "─" * 60)
    status = "PASS ✅" if not hard_fail else f"FAIL ❌ ({len(hard_fail)} regra(s) dura(s))"
    print(f"  Nota SEO/qualidade: {score}/100   →   {status}\n")
    return score, hard_fail


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    p = json.loads(open(args.spec, encoding="utf-8").read())
    checks, score, hard_fail = validate(p)
    if args.json:
        print(json.dumps({
            "slug": p.get("slug"), "score": score, "pass": not hard_fail,
            "checks": [{"name": n, "ok": o, "hard": h, "detail": d} for n, o, h, d in checks],
        }, ensure_ascii=False, indent=2))
    else:
        report(p)
    return 0 if not hard_fail else 1


if __name__ == "__main__":
    raise SystemExit(main())
