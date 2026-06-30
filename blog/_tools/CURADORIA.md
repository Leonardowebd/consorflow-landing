# Curadoria de qualidade — Blog Consorflow

Todo artigo passa por **duas camadas** antes de publicar. Só vai ao ar o que passa nas duas.

1. **Portão objetivo** (`validar_post.py`) — automático, bloqueia (regra dura).
2. **Régua editorial** (este doc) — julgamento de qualidade, avaliado pelo autor/curador antes do commit.

> Ordem do ciclo: pesquisar → escrever spec → **régua editorial (auto-revisão)** → `validar_post.py` (PASS) → gerar → publicar. Se reprovar em qualquer ponto, corrige e repete. Nunca publicar no `--force` sem decisão consciente.

---

## 1. Portão objetivo (resumo do que ele exige)

| Critério | Regra |
|---|---|
| Título | ≤ 65 chars (ideal 50–60), com a keyword |
| Meta description | 120–160 chars, com a keyword |
| Slug | kebab-case, ≤ 60, com a keyword |
| Estrutura | ≥ 3 H2, ≥ 50% em forma de pergunta |
| GEO/AEO | bloco-resposta de 30–60 palavras logo após o H2-pergunta |
| Profundidade | corpo ≥ 700 palavras (ideal ≥ 1000) |
| FAQ | ≥ 3 perguntas, respostas 30–60 palavras (vira FAQPage schema) |
| Links | ≥ 1 link interno |
| Keyword | presente em título, meta e 1º parágrafo; densidade < 4% (sem stuffing) |
| **Compliance** | **proibido** prometer contemplação, rentabilidade, retorno/lucro/ganho garantido, "sem risco" |

Rodar: `python3 blog/_tools/validar_post.py blog/_tools/posts/<slug>.json`

---

## 2. Régua editorial (o que o portão NÃO mede)

O portão garante o piso técnico. A régua garante que o conteúdo **merece ranquear** — é isso que o Google (Helpful Content + E-E-A-T) e os motores de IA premiam.

### Intenção de busca (a primeira pergunta)
- A pauta responde a uma **dúvida real** que o público-alvo (administradoras, corretoras, times comerciais e quem cogita consórcio) digitaria?
- Qual a **intenção**: informacional, comparativa ou transacional? O artigo entrega exatamente isso?
- O título promete e o conteúdo **cumpre** (sem clickbait)?

### Originalidade e profundidade (Helpful Content)
- Traz um **ângulo, dado ou enquadramento** que os concorrentes não têm? (não reescrever o óbvio)
- Tem **experiência/especificidade**: exemplos concretos do dia a dia comercial, números, passos acionáveis — não generalidades.
- Alguém da área leria e diria "isso me ajudou de verdade"?

### E-E-A-T (autoridade e confiança)
- Afirmações de dados (Selic, ABAC, BACEN, mercado) têm **fonte verificável e atual**? Pesquisar antes (WebSearch), nunca escrever de memória.
- Datas, taxas e estatísticas conferidas no momento da escrita.
- Tom de quem **entende de venda de consórcio**, não de quem está vendendo a qualquer custo.

### Linha editorial — a ponte dos 3 pilares
- **Pilar 1 (Notícias do mundo):** parte de um fato atual amplo e faz a **ponte por copy** até o consórcio. A ponte tem que ser natural, não forçada.
- **Pilar 2 (Mundo do consórcio):** notícia/dado do setor (ABAC, BACEN, regulação) com leitura útil para quem opera.
- **Pilar 3 (Tecnologia):** IA, CRM, WhatsApp, automação — onde a Consorflow encaixa, sem virar propaganda.
- Em todos: **valor primeiro, produto depois**. A Consorflow aparece como consequência natural, no máximo no bloco de CTA.

### Legibilidade e experiência
- Parágrafos curtos (2–4 linhas), frases diretas, voz ativa.
- Subtítulos escaneáveis; listas onde couber.
- Sem jargão sem explicação; sem enrolação para "bater palavra".
- Conteúdo > contagem: 700 palavras é piso, não meta — só escreva mais se agrega.

### Compliance e ética
- Consórcio **não é investimento**. Nunca prometer contemplação, rendimento, retorno ou "sem risco".
- Sem superlativos enganosos ("o melhor", "garantido", "infalível").
- Comparações (consórcio x financiamento) **justas e equilibradas**.

---

## Checklist final do curador (antes do commit)

- [ ] A pauta foi pesquisada e tem fonte atual (não escrita de memória)
- [ ] O ângulo é original e útil — não é o óbvio reembalado
- [ ] A ponte do pilar até o consórcio é natural
- [ ] Dados/datas conferidos
- [ ] Valor antes do produto; CTA sem promessa
- [ ] `validar_post.py` retornou **PASS**
- [ ] Eu publicaria isso com o meu nome
