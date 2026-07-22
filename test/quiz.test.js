"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const contract = require("../quiz-contract");
const { createHandler, validatePayload } = require("../api/quiz-leads")._test;

const EXPECTED_FIELDS = [
  "papel_operacao",
  "nivel_operacao",
  "tamanho_equipe_vendas",
  "faixa_faturamento_mensal",
  "lucro_mensal_20k",
  "maturidade_processo",
  "volume_leads_mensal",
  "principal_gargalo",
  "urgencia_implantacao",
  "capacidade_decisao"
];

function topAnswers(overrides = {}) {
  const answers = Object.fromEntries(contract.QUESTIONS.map(function (question) {
    return [question.field, question.options.reduce(function (best, option) {
      return option.points > best.points ? option : best;
    }).value];
  }));
  answers.principal_gargalo = "slow_first_response";
  return { ...answers, ...overrides };
}

function payload(overrides = {}) {
  const answers = overrides.answers || topAnswers();
  return {
    event: contract.EVENT_NAME,
    quiz_version: contract.QUIZ_VERSION,
    completed_at: "2026-07-22T15:00:00-03:00",
    contact: { name: "Pessoa Teste", email: "teste@example.com", whatsapp: "", company: "" },
    consent: {
      commercial_contact: false,
      captured_at: null,
      privacy_notice_version: contract.PRIVACY_NOTICE_VERSION,
      source: "landing_quiz"
    },
    qualification: contract.qualificationFromAnswers(answers),
    attribution: {
      landing_url: "https://consorflow.com/",
      referrer: "",
      utm_source: "",
      utm_medium: "",
      utm_campaign: "",
      utm_content: "",
      utm_term: "",
      gclid: "",
      fbclid: ""
    },
    ...overrides.body
  };
}

function responseRecorder() {
  return {
    statusCode: 200,
    headers: {},
    payload: null,
    status(code) { this.statusCode = code; return this; },
    setHeader(name, value) { this.headers[name] = value; },
    json(value) { this.payload = value; return this; }
  };
}

function request(body, eventId) {
  return {
    method: "POST",
    body,
    headers: {
      host: "consorflow.com",
      origin: "https://consorflow.com",
      "idempotency-key": eventId,
      "x-forwarded-for": "203.0.113.10"
    },
    socket: {}
  };
}

test("contrato tem versão, evento e dez field names exatos", () => {
  assert.equal(contract.QUIZ_VERSION, "consorflow-icp-v1.0");
  assert.equal(contract.EVENT_NAME, "landing_quiz_completed");
  assert.deepEqual(contract.FIELD_NAMES, EXPECTED_FIELDS);
  assert.equal(contract.QUESTIONS.length, 10);
});

test("pontuação máxima é 100 e resulta em priority", () => {
  const result = contract.scoreAnswers(topAnswers());
  assert.deepEqual(result, { score_total: 100, score_band: "priority", non_icp: false });
});

test("limites das quatro bandas são exatos", () => {
  assert.equal(contract.baseBand(29), "low_fit");
  assert.equal(contract.baseBand(30), "nurture");
  assert.equal(contract.baseBand(49), "nurture");
  assert.equal(contract.baseBand(50), "good_fit");
  assert.equal(contract.baseBand(74), "good_fit");
  assert.equal(contract.baseBand(75), "priority");
});

test("non_icp força low_fit independentemente da soma", () => {
  const result = contract.scoreAnswers(topAnswers({ papel_operacao: "outside_consortium_sales" }));
  assert.equal(result.non_icp, true);
  assert.equal(result.score_band, "low_fit");
});

test("no_influence impede priority e limita a good_fit", () => {
  const result = contract.scoreAnswers(topAnswers({ capacidade_decisao: "no_influence" }));
  assert.ok(result.score_total >= 75);
  assert.equal(result.score_band, "good_fit");
});

test("todos os enums aceitam somente values documentados", () => {
  for (const question of contract.QUESTIONS) {
    assert.ok(question.options.length >= 4);
    assert.equal(new Set(question.options.map(function (option) { return option.value; })).size, question.options.length);
    assert.equal(contract.optionFor(question.field, "__invalid__"), undefined);
  }
  assert.deepEqual(contract.validateAnswers(topAnswers()), []);
});

test("analytics remove PII, respostas e dados financeiros", () => {
  const event = contract.sanitizeAnalyticsEvent("quiz_step_completed", {
    step_number: 4,
    question_id: "faixa_faturamento_mensal",
    value: "above_250k",
    points: 10,
    name: "Pessoa",
    email: "pessoa@example.com",
    whatsapp: "+5577999999999",
    faixa_faturamento_mensal: "above_250k",
    lucro_mensal_20k: "above"
  });
  assert.deepEqual(Object.keys(event).sort(), ["event", "question_id", "quiz_version", "step_number"]);
  assert.equal(JSON.stringify(event).includes("above_250k"), false);
  assert.equal(JSON.stringify(event).includes("pessoa@example.com"), false);

  const poisonedStart = contract.sanitizeAnalyticsEvent("quiz_started", {
    entry_point: "pessoa@example.com",
    utm_source: "+55 77 99999-9999",
    utm_campaign: "campanha_segura"
  });
  assert.equal(poisonedStart.entry_point, undefined);
  assert.equal(poisonedStart.utm_source, undefined);
  assert.equal(poisonedStart.utm_campaign, "campanha_segura");
});

test("validador do endpoint recalcula score e rejeita adulteração", () => {
  const body = payload();
  body.qualification = { ...body.qualification, score_total: 99 };
  const result = validatePayload(body);
  assert.ok(result.errors.includes("invalid_score_total"));
});

test("endpoint indisponível não encaminha nem expõe PII", async () => {
  let calls = 0;
  const handler = createHandler({ env: {}, fetchImpl: async function () { calls += 1; } });
  const res = responseRecorder();
  await handler(request(payload(), "5f9a1b38-9ef8-4aa4-8dc6-1219fd84ab11"), res);
  assert.equal(res.statusCode, 503);
  assert.deepEqual(res.payload, { accepted: false, status: "unavailable", reason: "webhook_not_configured" });
  assert.equal(calls, 0);
  assert.equal(JSON.stringify(res.payload).includes("teste@example.com"), false);
});

test("endpoint encaminha uma vez com token, assinatura e chave idempotente", async () => {
  const calls = [];
  const fetchImpl = async function (url, options) {
    calls.push({ url, options });
    return { ok: true, json: async function () { return { lead_id: "lead-123" }; } };
  };
  const env = {
    QUIZ_WEBHOOK_URL: "https://hooks.example.com/quiz",
    QUIZ_WEBHOOK_TOKEN: "token-test",
    QUIZ_WEBHOOK_SIGNING_SECRET: "signing-test"
  };
  const handler = createHandler({ env, fetchImpl, now: function () { return 1000; } });
  const eventId = "d9647bd2-8105-43a1-a157-31d80473f07b";
  const first = responseRecorder();
  const second = responseRecorder();
  await handler(request(payload(), eventId), first);
  await handler(request(payload(), eventId), second);

  assert.equal(first.statusCode, 202);
  assert.equal(second.statusCode, 202);
  assert.equal(second.payload.duplicate, true);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].options.headers.Authorization, "Bearer token-test");
  assert.equal(calls[0].options.headers["Idempotency-Key"], eventId);
  const expectedSignature = "sha256=" + crypto.createHmac("sha256", "signing-test").update(calls[0].options.body).digest("hex");
  assert.equal(calls[0].options.headers["X-Consorflow-Signature"], expectedSignature);
});

test("endpoint rejeita origem cruzada antes de qualquer encaminhamento", async () => {
  let calls = 0;
  const handler = createHandler({
    env: { QUIZ_WEBHOOK_URL: "https://hooks.example.com/quiz", QUIZ_WEBHOOK_TOKEN: "token" },
    fetchImpl: async function () { calls += 1; }
  });
  const req = request(payload(), "aebfa1be-aa9e-4511-bb84-965d9b393f3a");
  req.headers.origin = "https://evil.example";
  const res = responseRecorder();
  await handler(req, res);
  assert.equal(res.statusCode, 403);
  assert.equal(calls, 0);
});
