"use strict";

const crypto = require("node:crypto");
const contract = require("../quiz-contract");

const IDEMPOTENCY_TTL_MS = 24 * 60 * 60 * 1000;
const RATE_WINDOW_MS = 60 * 1000;
const RATE_LIMIT = 10;
const MAX_BODY_BYTES = 32 * 1024;
const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const completed = new Map();
const inFlight = new Map();
const rateBuckets = new Map();

function json(res, status, payload) {
  res.status(status).json(payload);
}

function string(value, max) {
  return typeof value === "string" && value.trim().length <= max ? value.trim() : null;
}

function validDate(value) {
  return typeof value === "string" && !Number.isNaN(Date.parse(value));
}

function normalizePhone(value) {
  const input = string(value, 30);
  if (input === null) return null;
  if (!input) return "";
  const digits = input.replace(/\D/g, "");
  if (digits.length < 10 || digits.length > 15) return null;
  return "+" + digits;
}

function validateAttribution(value) {
  const keys = ["landing_url", "referrer", "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term", "gclid", "fbclid"];
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const result = {};
  for (const key of keys) {
    const parsed = string(value[key] || "", key === "landing_url" || key === "referrer" ? 1000 : 200);
    if (parsed === null) return null;
    result[key] = parsed;
  }
  return result;
}

function validatePayload(body) {
  const errors = [];
  if (!body || typeof body !== "object" || Array.isArray(body)) return { errors: ["invalid_body"] };
  if (body.event !== contract.EVENT_NAME) errors.push("invalid_event");
  if (body.quiz_version !== contract.QUIZ_VERSION) errors.push("invalid_quiz_version");
  if (!validDate(body.completed_at)) errors.push("invalid_completed_at");

  const contact = body.contact && typeof body.contact === "object" ? body.contact : {};
  const name = string(contact.name, 100);
  const email = string(contact.email, 160);
  const whatsapp = normalizePhone(contact.whatsapp || "");
  const company = string(contact.company || "", 120);
  if (!name) errors.push("invalid_name");
  if (!email || !EMAIL.test(email)) errors.push("invalid_email");
  if (whatsapp === null) errors.push("invalid_whatsapp");
  if (company === null) errors.push("invalid_company");

  const consent = body.consent && typeof body.consent === "object" ? body.consent : {};
  if (typeof consent.commercial_contact !== "boolean") errors.push("invalid_commercial_contact");
  if (consent.source !== "landing_quiz") errors.push("invalid_consent_source");
  if (consent.privacy_notice_version !== contract.PRIVACY_NOTICE_VERSION) errors.push("invalid_privacy_notice_version");
  if (consent.commercial_contact && !validDate(consent.captured_at)) errors.push("invalid_consent_timestamp");
  if (!consent.commercial_contact && consent.captured_at !== null) errors.push("unexpected_consent_timestamp");

  const qualification = body.qualification && typeof body.qualification === "object" ? body.qualification : {};
  const answers = Object.fromEntries(contract.FIELD_NAMES.map(function (field) { return [field, qualification[field]]; }));
  const invalidFields = contract.validateAnswers(answers);
  if (invalidFields.length) errors.push("invalid_qualification_fields");
  let calculated = null;
  if (!invalidFields.length) {
    calculated = contract.scoreAnswers(answers);
    if (qualification.score_total !== calculated.score_total) errors.push("invalid_score_total");
    if (qualification.score_band !== calculated.score_band) errors.push("invalid_score_band");
    if (qualification.non_icp !== calculated.non_icp) errors.push("invalid_non_icp");
  }

  const attribution = validateAttribution(body.attribution);
  if (!attribution) errors.push("invalid_attribution");
  if (errors.length) return { errors };

  return {
    errors: [],
    payload: {
      event: contract.EVENT_NAME,
      quiz_version: contract.QUIZ_VERSION,
      completed_at: new Date(body.completed_at).toISOString(),
      contact: { name, email: email.toLowerCase(), whatsapp, company },
      consent: {
        commercial_contact: consent.commercial_contact,
        captured_at: consent.commercial_contact ? new Date(consent.captured_at).toISOString() : null,
        privacy_notice_version: contract.PRIVACY_NOTICE_VERSION,
        source: "landing_quiz"
      },
      qualification: { ...calculated, ...answers },
      attribution
    }
  };
}

function sameOrigin(req) {
  const origin = req.headers && (req.headers.origin || req.headers.Origin);
  const host = req.headers && (req.headers.host || req.headers.Host);
  if (!origin || !host) return true;
  try { return new URL(origin).host === host; } catch (_) { return false; }
}

function clientIp(req) {
  const forwarded = req.headers && req.headers["x-forwarded-for"];
  return String(Array.isArray(forwarded) ? forwarded[0] : forwarded || req.socket && req.socket.remoteAddress || "unknown").split(",")[0].trim();
}

function rateLimited(ip, now) {
  const current = rateBuckets.get(ip);
  if (!current || now - current.startedAt >= RATE_WINDOW_MS) {
    rateBuckets.set(ip, { startedAt: now, count: 1 });
    return false;
  }
  current.count += 1;
  return current.count > RATE_LIMIT;
}

function cleanCaches(now) {
  for (const [key, value] of completed) if (now - value.savedAt >= IDEMPOTENCY_TTL_MS) completed.delete(key);
  for (const [key, value] of rateBuckets) if (now - value.startedAt >= RATE_WINDOW_MS) rateBuckets.delete(key);
}

function webhookConfig(env) {
  const url = env.QUIZ_WEBHOOK_URL || "";
  const token = env.QUIZ_WEBHOOK_TOKEN || "";
  let parsed;
  try { parsed = new URL(url); } catch (_) { parsed = null; }
  if (!parsed || parsed.protocol !== "https:") return { ready: false, reason: "webhook_not_configured" };
  if (!token) return { ready: false, reason: "webhook_auth_not_configured" };
  return { ready: true, url: parsed.toString(), token, signingSecret: env.QUIZ_WEBHOOK_SIGNING_SECRET || "" };
}

async function forwardPayload(config, eventId, payload, fetchImpl) {
  const raw = JSON.stringify(payload);
  const headers = {
    "Authorization": "Bearer " + config.token,
    "Content-Type": "application/json",
    "Idempotency-Key": eventId,
    "X-Consorflow-Event": contract.EVENT_NAME,
    "X-Consorflow-Quiz-Version": contract.QUIZ_VERSION
  };
  if (config.signingSecret) {
    headers["X-Consorflow-Signature"] = "sha256=" + crypto.createHmac("sha256", config.signingSecret).update(raw).digest("hex");
  }
  const controller = new AbortController();
  const timeout = setTimeout(function () { controller.abort(); }, 8000);
  try {
    const response = await fetchImpl(config.url, { method: "POST", headers, body: raw, signal: controller.signal });
    if (!response.ok) throw new Error("downstream_rejected");
    const result = await response.json().catch(function () { return {}; });
    return { leadId: typeof result.lead_id === "string" ? result.lead_id.slice(0, 160) : null };
  } finally {
    clearTimeout(timeout);
  }
}

function createHandler(options = {}) {
  const env = options.env || process.env;
  const fetchImpl = options.fetchImpl || global.fetch;
  const now = options.now || Date.now;

  return async function handler(req, res) {
    if (req.method !== "POST") {
      res.setHeader("Allow", "POST");
      json(res, 405, { accepted: false, status: "method_not_allowed" });
      return;
    }
    if (!sameOrigin(req)) {
      json(res, 403, { accepted: false, status: "origin_not_allowed" });
      return;
    }

    const eventId = String(req.headers && (req.headers["idempotency-key"] || req.headers["Idempotency-Key"]) || "");
    if (!UUID_V4.test(eventId)) {
      json(res, 400, { accepted: false, status: "invalid_idempotency_key" });
      return;
    }
    const rawSize = Buffer.byteLength(JSON.stringify(req.body || {}));
    if (rawSize > MAX_BODY_BYTES) {
      json(res, 413, { accepted: false, status: "payload_too_large" });
      return;
    }

    const timestamp = now();
    cleanCaches(timestamp);
    if (completed.has(eventId)) {
      const cached = completed.get(eventId);
      json(res, 202, { accepted: true, duplicate: true, lead_id: cached.leadId, next: "whatsapp" });
      return;
    }
    if (inFlight.has(eventId)) {
      try {
        const pending = await inFlight.get(eventId);
        json(res, 202, { accepted: true, duplicate: true, lead_id: pending.leadId, next: "whatsapp" });
      } catch (_) {
        json(res, 502, { accepted: false, status: "forward_failed" });
      }
      return;
    }
    if (rateLimited(clientIp(req), timestamp)) {
      res.setHeader("Retry-After", "60");
      json(res, 429, { accepted: false, status: "rate_limited" });
      return;
    }

    const validation = validatePayload(req.body);
    if (validation.errors.length) {
      json(res, 400, { accepted: false, status: "invalid_payload", errors: validation.errors });
      return;
    }

    const config = webhookConfig(env);
    if (!config.ready) {
      json(res, 503, { accepted: false, status: "unavailable", reason: config.reason });
      return;
    }
    if (typeof fetchImpl !== "function") {
      json(res, 503, { accepted: false, status: "unavailable", reason: "fetch_unavailable" });
      return;
    }

    const operation = forwardPayload(config, eventId, validation.payload, fetchImpl);
    inFlight.set(eventId, operation);
    try {
      const forwarded = await operation;
      completed.set(eventId, { leadId: forwarded.leadId, savedAt: timestamp });
      json(res, 202, { accepted: true, duplicate: false, lead_id: forwarded.leadId, next: "whatsapp" });
    } catch (_) {
      json(res, 502, { accepted: false, status: "forward_failed" });
    } finally {
      inFlight.delete(eventId);
    }
  };
}

const handler = createHandler();
module.exports = handler;
module.exports._test = { createHandler, normalizePhone, validatePayload, webhookConfig };
