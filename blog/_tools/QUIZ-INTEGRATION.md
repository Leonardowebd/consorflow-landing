# Contrato técnico — quiz da landing (rodada 2)

## Fonte da verdade e estado atual

A implementação deve reproduzir exatamente `Skills/comercial/references/quiz-qualificacao-landing.md`, sem reinterpretar perguntas, valores, pesos, faixas ou consentimento.

- `quiz_version`: `consorflow-icp-v1.0`
- Total: 10 perguntas, uma resposta por pergunta.
- Evento CRM: `landing_quiz_completed`.
- Nota: `score_total`, de 0 a 100, somando Q1-Q7, Q9 e Q10. Q8 personaliza o resultado e não pontua.
- Bandas: `priority` (75-100), `good_fit` (50-74), `nurture` (30-49) e `low_fit` (0-29).
- Overrides: `non_icp = true` força `low_fit`; `capacidade_decisao = no_influence` impede `priority` e limita o resultado a `good_fit`.

`page.html` ainda é uma landing estática, sem quiz, formulário de lead ou endpoint próprio. Nenhuma UI foi alterada nesta rodada.

## Ponto exato de integração

O primeiro ponto permanece o CTA dinâmico da calculadora de planos:

- Elemento: `#reco-cbtn` (`Receba sua proposta`).
- Estado existente: `#vol-slider`, `idx`, `plans[idx]` e `volLabels[idx]` na função `update()`.
- Na implementação, o clique abrirá o quiz com `entry_point=pricing_calculator` apenas como contexto técnico/telemetria. O volume selecionado não preenche respostas, não altera pontos e não produz recomendação paralela.
- O `href` de WhatsApp atual permanece como fallback quando JavaScript, modal ou backend falharem.

CTAs secundários poderão reutilizar o mesmo controlador com `data-quiz-entry`: `.plan .pbtn`, `.hero-content .btn3d-face`, `.navcta-face`, `.navmenu-cta`, `.lig-btns .btn-primary` e `.cta-btn-w`. Não duplicar regras de score por botão.

## Dez campos de qualificação

Ordem e nomes exatos enviados em `qualification`:

1. `papel_operacao`
2. `nivel_operacao`
3. `tamanho_equipe_vendas`
4. `faixa_faturamento_mensal`
5. `lucro_mensal_20k`
6. `maturidade_processo`
7. `volume_leads_mensal`
8. `principal_gargalo`
9. `urgencia_implantacao`
10. `capacidade_decisao`

As opções, `value` e `points` desses campos devem vir literalmente do documento comercial. Não criar campos paralelos de qualificação nem uma recomendação de plano fora das quatro bandas oficiais.

## Contrato de transporte e CRM

Endpoint previsto para a rodada 2: `POST /api/quiz-leads`. Enviar `Idempotency-Key: <uuid-v4>` no header; o backend persiste a chave e devolve o mesmo `lead_id` em reenvios.

Payload funcional:

```json
{
  "event": "landing_quiz_completed",
  "quiz_version": "consorflow-icp-v1.0",
  "completed_at": "2026-07-22T15:00:00-03:00",
  "contact": {
    "name": "",
    "email": "",
    "whatsapp": "",
    "company": ""
  },
  "consent": {
    "commercial_contact": false,
    "captured_at": null,
    "privacy_notice_version": "",
    "source": "landing_quiz"
  },
  "qualification": {
    "score_total": 0,
    "score_band": "priority|good_fit|nurture|low_fit",
    "non_icp": false,
    "papel_operacao": "",
    "nivel_operacao": "",
    "tamanho_equipe_vendas": "",
    "faixa_faturamento_mensal": "",
    "lucro_mensal_20k": "",
    "maturidade_processo": "",
    "volume_leads_mensal": "",
    "principal_gargalo": "",
    "urgencia_implantacao": "",
    "capacidade_decisao": ""
  },
  "attribution": {
    "landing_url": "",
    "referrer": "",
    "utm_source": "",
    "utm_medium": "",
    "utm_campaign": "",
    "utm_content": "",
    "utm_term": "",
    "gclid": "",
    "fbclid": ""
  }
}
```

## Eventos analíticos

Analytics nunca recebe nome, e-mail, WhatsApp, empresa, respostas individuais ou valores/faixas de faturamento e lucro.

- `quiz_started`: `quiz_version`, `entry_point`, `utm_*`.
- `quiz_step_completed`: `quiz_version`, `step_number`, `question_id`; sem `value`, pontos ou resposta financeira.
- `quiz_completed`: `quiz_version`, `score_band`, `non_icp`.
- `quiz_result_cta_clicked`: `quiz_version`, `score_band`, `cta_id`.
- `quiz_lead_submitted`: `quiz_version`, `score_band`, `commercial_contact`; sem PII.

`question_id` deve ser somente o `field_name`. Para Q4 e Q5, registrar apenas que a etapa foi concluída, nunca a resposta, faixa, pontos ou derivação financeira.

## Resposta, segurança e fallback

- `202`: `{ "accepted": true, "lead_id": "...", "next": "whatsapp|calendar" }`.
- `400`: versão, campo, enum ou consentimento inválido; não persistir parcialmente.
- `409`: chave idempotente já processada; devolver o `lead_id` existente.
- `429`: limitar por IP e chave idempotente, com `Retry-After`.
- `5xx`/offline: manter o resultado na tela, enfileirar reenvio e preservar o WhatsApp fallback sem duplicar o lead.
- Validar no servidor `quiz_version`, os dez campos, valores permitidos, score, bandas e overrides. O cliente não decide a faixa final sozinho.
- Não colocar PII, respostas ou score em query string, logs, pixels ou data layer.
- Consentimento comercial começa desmarcado; preservar `captured_at`, versão do aviso e histórico.
- Nome e e-mail são obrigatórios após o resultado; WhatsApp e empresa são opcionais. Nunca bloquear a nota pela ausência de telefone.
- Normalizar WhatsApp antes da deduplicação; deduplicar por e-mail ou WhatsApp normalizado e manter a submissão mais recente.
- Restringir respostas financeiras no CRM por função e pela política de retenção aprovada.
- Sanitizar `principal_gargalo=other` e qualquer texto livre, com limite de 300 caracteres.
- Variáveis esperadas: `QUIZ_WEBHOOK_URL`, `QUIZ_WEBHOOK_TOKEN` e opcional `QUIZ_WEBHOOK_SIGNING_SECRET`, somente no ambiente da hospedagem.

## Checagem determinística obrigatória

A rodada 2 só passa se uma validação automatizada confirmar:

1. `quiz_version === "consorflow-icp-v1.0"`.
2. Existem exatamente 10 `field_name`, na ordem documentada acima.
3. O payload usa `event === "landing_quiz_completed"`.
4. Os limites 29/30, 49/50 e 74/75 estão corretos.
5. `non_icp` e `no_influence` aplicam os overrides.
6. Eventos analíticos não contêm PII nem respostas financeiras.
