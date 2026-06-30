# Guia — Geração automática de post do blog Consorflow

Este guia torna o ciclo autossuficiente para um agente que só tem o repositório clonado.

## Contexto da marca
Consorflow = CRM/plataforma de gestão comercial para administradoras e corretoras de **consórcio** no Brasil (leads, WhatsApp, IA de qualificação, funil). Tom B2B, direto, sem jargão. Vocabulário do setor: carta de crédito, contemplação, lance, grupo, administradora, taxa de administração, follow-up, funil, SLA.
**Compliance:** nunca prometer contemplação, rentabilidade ou resultado garantido. Posicionar como organização da operação comercial.

## 3 pilares (rodar em rodízio)
1. **Notícias do mundo → ponte para o consórcio** (juros/Selic, economia, mercado imobiliário/automóvel). Técnica: gancho → ponte → aterrissagem na Consorflow.
2. **Mundo do consórcio** (ABAC, BACEN, dados/tendências do setor).
3. **Tecnologia aplicada ao consórcio** (IA, CRM, WhatsApp, automação).

## Passos do ciclo
1. **Pesquisar (WebSearch)**: uma pauta atual relevante ao pilar da vez + boas práticas de SEO/GEO do momento. Não escrever de memória.
2. **Escrever a spec** `blog/_tools/posts/<slug>.json` (schema abaixo).
3. **Gerar**: primeiro garanta a dependência da capa — `pip install Pillow` (gera a capa PNG editorial automaticamente). Depois:
   `python3 blog/_tools/gerar_post.py blog/_tools/posts/<slug>.json --site .`
   (o `--site .` é obrigatório na nuvem: o site é a raiz do repo clonado.)
4. **Conferir AVISOS GEO** impressos (blocos fora de 30-60 palavras) e ajustar a spec se preciso.
5. **Publicar**: `git add -A && git commit -m "blog: <título>" && git push origin main`.
   A Vercel publica automaticamente no push em `main`.

## Regras SEO/GEO (obrigatórias)
- `title` 50-60 chars com a intenção de busca; `meta_description` 120-160 chars.
- Cada seção: **H2 em forma de pergunta** + `answer` de **30-60 palavras** (vira bloco GEO + entra no FAQPage).
- Link interno para a home e CTA (o script injeta o CTA).
- `date` = data real do dia (use `date +%F`).

## Schema da spec JSON
```json
{
  "slug": "kebab-case",
  "title": "...", "meta_description": "...", "dek": "...",
  "pillar": "Notícias do mundo | Mundo do consórcio | Tecnologia",
  "date": "AAAA-MM-DD", "read_min": 6, "image": "/asset_dash.jpg",
  "sections": [
    {"h2": "Pergunta?", "answer": "Resposta 30-60 palavras.", "paras": ["..."], "h3": "opcional", "list": ["..."]}
  ],
  "faq": [{"q": "Pergunta?", "a": "Resposta 30-60 palavras."}]
}
```
Imagens disponíveis na raiz do repo: `/asset_dash.jpg`, `/asset_funil_kanban.webp`, `/asset_funil_leads.webp`, `/asset_funil_agentes.webp`.
