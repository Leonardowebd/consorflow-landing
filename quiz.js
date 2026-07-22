(function () {
  "use strict";

  const contract = window.ConsorflowQuizContract;
  if (!contract) return;

  const STORAGE_KEY = "consorflow_landing_quiz_v1";
  const WHATSAPP_URL = "https://wa.me/5577981454387?text=" + encodeURIComponent("Olá! Concluí o quiz da Consorflow e gostaria de conversar sobre o resultado.");
  const DEFAULT_STATE = { mode: "intro", step: 0, answers: {}, entryPoint: "pricing_calculator", eventId: "" };
  const state = loadState();
  let overlay = null;
  let dialog = null;
  let body = null;
  let progressWrap = null;
  let progressText = null;
  let progressBar = null;
  let liveRegion = null;
  let previousFocus = null;

  function loadState() {
    try {
      const parsed = JSON.parse(sessionStorage.getItem(STORAGE_KEY) || "null");
      if (!parsed || parsed.quizVersion !== contract.QUIZ_VERSION) return { ...DEFAULT_STATE };
      const answers = {};
      contract.FIELD_NAMES.forEach(function (field) {
        if (contract.optionFor(field, parsed.answers && parsed.answers[field])) answers[field] = parsed.answers[field];
      });
      return {
        ...DEFAULT_STATE,
        mode: ["intro", "question", "result", "form", "submitted"].includes(parsed.mode) ? parsed.mode : "intro",
        step: Math.max(0, Math.min(9, Number(parsed.step) || 0)),
        answers,
        entryPoint: String(parsed.entryPoint || DEFAULT_STATE.entryPoint).slice(0, 80),
        eventId: String(parsed.eventId || "").slice(0, 80)
      };
    } catch (_) {
      return { ...DEFAULT_STATE };
    }
  }

  function saveState() {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
        quizVersion: contract.QUIZ_VERSION,
        mode: state.mode,
        step: state.step,
        answers: state.answers,
        entryPoint: state.entryPoint,
        eventId: state.eventId
      }));
    } catch (_) {}
  }

  function analytics(eventName, properties) {
    if (!window.dataLayer || typeof window.dataLayer.push !== "function") return;
    const event = contract.sanitizeAnalyticsEvent(eventName, properties || {});
    if (event) window.dataLayer.push(event);
  }

  function utmProperties() {
    const params = new URLSearchParams(window.location.search);
    return {
      utm_source: params.get("utm_source") || "",
      utm_medium: params.get("utm_medium") || "",
      utm_campaign: params.get("utm_campaign") || "",
      utm_content: params.get("utm_content") || "",
      utm_term: params.get("utm_term") || ""
    };
  }

  function attribution() {
    const params = new URLSearchParams(window.location.search);
    return {
      landing_url: window.location.href.split("#")[0],
      referrer: document.referrer || "",
      utm_source: params.get("utm_source") || "",
      utm_medium: params.get("utm_medium") || "",
      utm_campaign: params.get("utm_campaign") || "",
      utm_content: params.get("utm_content") || "",
      utm_term: params.get("utm_term") || "",
      gclid: params.get("gclid") || "",
      fbclid: params.get("fbclid") || ""
    };
  }

  function ensureUi() {
    if (overlay) return;
    overlay = document.createElement("div");
    overlay.className = "cq-overlay";
    overlay.hidden = true;
    overlay.innerHTML = [
      '<section class="cq-dialog" role="dialog" aria-modal="true" aria-labelledby="cq-title" aria-describedby="cq-live">',
      '  <header class="cq-header">',
      '    <div class="cq-brand"><img src="asset_navlogo.svg" alt="Consorflow"></div>',
      '    <button class="cq-close" type="button" aria-label="Fechar quiz">&times;</button>',
      '  </header>',
      '  <div class="cq-progress-wrap" hidden>',
      '    <div class="cq-progress-meta"><span class="cq-progress-text"></span><span>Cerca de 2 minutos</span></div>',
      '    <div class="cq-progress" role="progressbar" aria-valuemin="1" aria-valuemax="10" aria-valuenow="1"><span class="cq-progress-bar"></span></div>',
      '  </div>',
      '  <div class="cq-body"></div>',
      '  <div class="cq-sr-only" id="cq-live" aria-live="polite" aria-atomic="true"></div>',
      '</section>'
    ].join("");
    document.body.appendChild(overlay);
    dialog = overlay.querySelector(".cq-dialog");
    body = overlay.querySelector(".cq-body");
    progressWrap = overlay.querySelector(".cq-progress-wrap");
    progressText = overlay.querySelector(".cq-progress-text");
    progressBar = overlay.querySelector(".cq-progress-bar");
    liveRegion = overlay.querySelector("#cq-live");
    overlay.querySelector(".cq-close").addEventListener("click", closeQuiz);
    overlay.addEventListener("mousedown", function (event) { if (event.target === overlay) closeQuiz(); });
    overlay.addEventListener("keydown", handleDialogKeydown);
  }

  function announce(text) {
    liveRegion.textContent = "";
    window.setTimeout(function () { liveRegion.textContent = text; }, 20);
  }

  function openQuiz(trigger) {
    ensureUi();
    previousFocus = trigger || document.activeElement;
    state.entryPoint = trigger && trigger.dataset.quizEntry || (trigger && trigger.id === "reco-cbtn" ? "pricing_calculator" : state.entryPoint);
    saveState();
    overlay.hidden = false;
    document.body.classList.add("cq-open");
    render();
  }

  function closeQuiz() {
    if (!overlay || overlay.hidden) return;
    overlay.hidden = true;
    document.body.classList.remove("cq-open");
    saveState();
    if (previousFocus && typeof previousFocus.focus === "function") previousFocus.focus();
  }

  function handleDialogKeydown(event) {
    if (event.key === "Escape") {
      event.preventDefault();
      closeQuiz();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = Array.from(dialog.querySelectorAll('button:not([disabled]), a[href], input:not([disabled])')).filter(function (element) {
      return element.offsetParent !== null;
    });
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }

  function setProgress(visible, step) {
    progressWrap.hidden = !visible;
    if (!visible) return;
    const current = step + 1;
    progressText.textContent = "Pergunta " + current + " de 10";
    progressBar.style.width = (current * 10) + "%";
    const progress = overlay.querySelector(".cq-progress");
    progress.setAttribute("aria-valuenow", String(current));
    progress.setAttribute("aria-valuetext", "Pergunta " + current + " de 10");
  }

  function render() {
    if (state.mode === "question") renderQuestion();
    else if (state.mode === "result") renderResult();
    else if (state.mode === "form") renderForm();
    else if (state.mode === "submitted") renderSubmitted();
    else renderIntro();
    body.scrollTop = 0;
  }

  function focusHeading() {
    const heading = body.querySelector("h2");
    if (heading) {
      heading.setAttribute("tabindex", "-1");
      heading.focus({ preventScroll: true });
    }
  }

  function renderIntro() {
    setProgress(false, 0);
    body.innerHTML = [
      '<p class="cq-eyebrow">Avaliação orientativa</p>',
      '<h2 class="cq-title" id="cq-title">Sua operação está pronta para escalar com processo?</h2>',
      '<p class="cq-lead">Responda 10 perguntas. Leva cerca de 2 minutos.</p>',
      '<div class="cq-actions"><button class="cq-button cq-button-primary" type="button" data-action="start">Avaliar minha operação</button></div>'
    ].join("");
    body.querySelector('[data-action="start"]').addEventListener("click", function () {
      state.mode = "question";
      state.step = Math.max(0, Math.min(state.step, 9));
      analytics("quiz_started", { ...utmProperties(), entry_point: state.entryPoint });
      saveState();
      renderQuestion();
    });
    announce("Quiz aberto.");
    focusHeading();
  }

  function renderQuestion() {
    const question = contract.QUESTIONS[state.step];
    const selected = state.answers[question.field] || "";
    setProgress(true, state.step);
    const notice = question.financial
      ? '<p class="cq-notice" id="cq-financial-notice">Use apenas uma faixa. Não precisamos de valores exatos. Você também pode escolher “Prefiro não informar”.</p>'
      : "";
    const options = question.options.map(function (option, index) {
      const id = "cq-option-" + state.step + "-" + index;
      return '<label class="cq-option" for="' + id + '">' +
        '<input id="' + id + '" type="radio" name="' + question.field + '" value="' + option.value + '"' + (selected === option.value ? " checked" : "") + '>' +
        '<span>' + option.label + '</span></label>';
    }).join("");
    body.innerHTML = [
      '<p class="cq-eyebrow">Pergunta ' + (state.step + 1) + ' de 10</p>',
      '<h2 class="cq-title cq-question-title" id="cq-title">' + question.question + '</h2>',
      notice,
      '<fieldset class="cq-options" aria-labelledby="cq-title"' + (question.financial ? ' aria-describedby="cq-financial-notice"' : "") + '><legend class="cq-sr-only">Escolha uma opção</legend>' + options + '</fieldset>',
      '<div class="cq-actions">' +
        (state.step > 0 ? '<button class="cq-button cq-button-secondary" type="button" data-action="back">Voltar</button>' : '') +
        '<button class="cq-button cq-button-primary" type="button" data-action="next"' + (selected ? "" : " disabled") + '>' + (state.step === 9 ? "Ver meu resultado" : "Continuar") + '</button>' +
      '</div>'
    ].join("");

    body.querySelectorAll('input[type="radio"]').forEach(function (input) {
      input.addEventListener("change", function () {
        state.answers[question.field] = input.value;
        body.querySelector('[data-action="next"]').disabled = false;
        saveState();
      });
    });
    const back = body.querySelector('[data-action="back"]');
    if (back) back.addEventListener("click", function () { state.step -= 1; saveState(); renderQuestion(); });
    body.querySelector('[data-action="next"]').addEventListener("click", nextQuestion);
    announce("Pergunta " + (state.step + 1) + " de 10. " + question.question);
    focusHeading();
  }

  function nextQuestion() {
    const question = contract.QUESTIONS[state.step];
    if (!contract.optionFor(question.field, state.answers[question.field])) return;
    analytics("quiz_step_completed", {
      step_number: state.step + 1,
      question_id: question.field
    });
    if (state.step < 9) {
      state.step += 1;
      saveState();
      renderQuestion();
      return;
    }
    state.mode = "result";
    saveState();
    const result = contract.scoreAnswers(state.answers);
    analytics("quiz_completed", { score_band: result.score_band, non_icp: result.non_icp });
    renderResult();
  }

  function resultMarkup(compact) {
    const score = contract.scoreAnswers(state.answers);
    const result = contract.RESULTS[score.score_band];
    const bottleneck = contract.GARGALO_LABELS[state.answers.principal_gargalo] || "Processo comercial";
    return [
      '<div class="cq-result-card">',
      '  <span class="cq-result-band">' + result.label + '</span>',
      '  <p><strong>' + result.title + '</strong></p>',
      compact ? "" : '<p>' + result.message + '</p>',
      compact ? "" : '<p>O primeiro ponto a revisar: <strong>' + bottleneck + '</strong>.</p>',
      '</div>'
    ].join("");
  }

  function renderResult() {
    setProgress(false, 0);
    const score = contract.scoreAnswers(state.answers);
    const result = contract.RESULTS[score.score_band];
    const lowFit = score.score_band === "low_fit";
    body.innerHTML = [
      '<p class="cq-eyebrow">Seu resultado</p>',
      '<h2 class="cq-title" id="cq-title">' + result.title + '</h2>',
      resultMarkup(false),
      '<p class="cq-disclaimer">A avaliação é orientativa e usa apenas as respostas informadas. Não representa garantia de resultado.</p>',
      '<div class="cq-actions">',
      lowFit
        ? '<a class="cq-button cq-button-primary" href="/blog/" data-result-cta="practical_guide">' + result.primaryCta + '</a>'
        : '<button class="cq-button cq-button-primary" type="button" data-result-cta="primary_capture">' + result.primaryCta + '</button>',
      result.secondaryCta
        ? (score.score_band === "nurture"
          ? '<a class="cq-button cq-button-secondary" href="/" data-result-cta="learn_consorflow">' + result.secondaryCta + '</a>'
          : '<a class="cq-button cq-button-secondary" href="' + WHATSAPP_URL + '" target="_blank" rel="noopener" data-result-cta="whatsapp">' + result.secondaryCta + '</a>')
        : "",
      lowFit ? '<button class="cq-button cq-button-secondary" type="button" data-result-cta="email_result">Receber resultado por e-mail</button>' : "",
      '</div>'
    ].join("");
    body.querySelectorAll("[data-result-cta]").forEach(function (element) {
      element.addEventListener("click", function () {
        analytics("quiz_result_cta_clicked", { score_band: score.score_band, cta_id: element.dataset.resultCta });
        if (element.tagName === "BUTTON") {
          state.mode = "form";
          saveState();
          renderForm();
        }
      });
    });
    announce("Resultado: " + result.label + ". " + result.title);
    focusHeading();
  }

  function renderForm() {
    setProgress(false, 0);
    body.innerHTML = [
      '<p class="cq-eyebrow">Receba seu resultado</p>',
      '<h2 class="cq-title cq-question-title" id="cq-title">Para onde enviamos o próximo passo?</h2>',
      resultMarkup(true),
      '<form class="cq-form" novalidate>',
      '  <div class="cq-grid">',
      '    <div class="cq-field"><label for="cq-name">Nome *</label><input class="cq-input" id="cq-name" name="name" autocomplete="name" maxlength="100" required></div>',
      '    <div class="cq-field"><label for="cq-email">E-mail *</label><input class="cq-input" id="cq-email" name="email" type="email" autocomplete="email" maxlength="160" required></div>',
      '    <div class="cq-field"><label for="cq-whatsapp">WhatsApp <span aria-hidden="true">(opcional)</span></label><input class="cq-input" id="cq-whatsapp" name="whatsapp" type="tel" autocomplete="tel" maxlength="30"></div>',
      '    <div class="cq-field"><label for="cq-company">Empresa <span aria-hidden="true">(opcional)</span></label><input class="cq-input" id="cq-company" name="company" autocomplete="organization" maxlength="120"></div>',
      '  </div>',
      '  <label class="cq-check"><input name="commercial_contact" type="checkbox"><span>Autorizo a Consorflow a usar estes dados para enviar meu resultado e falar sobre a operação. Posso cancelar a qualquer momento.</span></label>',
      '  <p class="cq-privacy">O consentimento comercial é opcional e começa desmarcado. Aviso de privacidade: ' + contract.PRIVACY_NOTICE_VERSION + '.</p>',
      '  <div class="cq-status" role="status" aria-live="polite"></div>',
      '  <div class="cq-actions"><button class="cq-button cq-button-secondary" type="button" data-action="result">Voltar ao resultado</button><button class="cq-button cq-button-primary" type="submit">Enviar resultado</button></div>',
      '</form>'
    ].join("");
    const form = body.querySelector("form");
    body.querySelector('[data-action="result"]').addEventListener("click", function () { state.mode = "result"; saveState(); renderResult(); });
    form.addEventListener("submit", submitLead);
    announce("Formulário opcional após o resultado. Nome e e-mail são obrigatórios.");
    focusHeading();
  }

  function uuid() {
    if (window.crypto && typeof window.crypto.randomUUID === "function") return window.crypto.randomUUID();
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (character) {
      const random = Math.random() * 16 | 0;
      return (character === "x" ? random : (random & 3 | 8)).toString(16);
    });
  }

  function validateForm(form) {
    let valid = true;
    form.querySelectorAll("[required]").forEach(function (input) {
      const fieldValid = input.value.trim() && (input.type !== "email" || input.validity.valid);
      input.setAttribute("aria-invalid", fieldValid ? "false" : "true");
      if (!fieldValid) valid = false;
    });
    return valid;
  }

  async function submitLead(event) {
    event.preventDefault();
    const form = event.currentTarget;
    const status = form.querySelector(".cq-status");
    if (!validateForm(form)) {
      status.dataset.kind = "error";
      status.textContent = "Revise o nome e o e-mail antes de continuar.";
      const invalid = form.querySelector('[aria-invalid="true"]');
      if (invalid) invalid.focus();
      return;
    }

    const formData = new FormData(form);
    const commercialContact = formData.get("commercial_contact") === "on";
    const score = contract.scoreAnswers(state.answers);
    const payload = {
      event: contract.EVENT_NAME,
      quiz_version: contract.QUIZ_VERSION,
      completed_at: new Date().toISOString(),
      contact: {
        name: String(formData.get("name") || "").trim(),
        email: String(formData.get("email") || "").trim(),
        whatsapp: String(formData.get("whatsapp") || "").trim(),
        company: String(formData.get("company") || "").trim()
      },
      consent: {
        commercial_contact: commercialContact,
        captured_at: commercialContact ? new Date().toISOString() : null,
        privacy_notice_version: contract.PRIVACY_NOTICE_VERSION,
        source: "landing_quiz"
      },
      qualification: contract.qualificationFromAnswers(state.answers),
      attribution: attribution()
    };

    state.eventId = state.eventId || uuid();
    saveState();
    const submit = form.querySelector('[type="submit"]');
    submit.disabled = true;
    status.dataset.kind = "";
    status.textContent = "Enviando…";

    try {
      const response = await fetch("/api/quiz-leads", {
        method: "POST",
        headers: { "Content-Type": "application/json", "Idempotency-Key": state.eventId },
        body: JSON.stringify(payload)
      });
      const result = await response.json().catch(function () { return {}; });
      if (!response.ok || !result.accepted) throw new Error(result.status || "request_failed");
      analytics("quiz_lead_submitted", { score_band: score.score_band, commercial_contact: commercialContact });
      state.mode = "submitted";
      saveState();
      renderSubmitted();
    } catch (_) {
      submit.disabled = false;
      status.dataset.kind = "error";
      status.innerHTML = 'Não foi possível enviar agora. Seu resultado continua disponível. <a href="' + WHATSAPP_URL + '" target="_blank" rel="noopener">Falar pelo WhatsApp</a>.';
    }
  }

  function renderSubmitted() {
    setProgress(false, 0);
    body.innerHTML = [
      '<p class="cq-eyebrow">Resultado enviado</p>',
      '<h2 class="cq-title" id="cq-title">Recebemos suas informações.</h2>',
      resultMarkup(true),
      '<p class="cq-lead">A equipe seguirá o tratamento indicado para esta faixa. Se preferir, você também pode falar conosco agora.</p>',
      '<div class="cq-actions"><a class="cq-button cq-button-primary" href="' + WHATSAPP_URL + '" target="_blank" rel="noopener">Falar pelo WhatsApp</a><button class="cq-button cq-button-secondary" type="button" data-action="close">Fechar</button></div>'
    ].join("");
    body.querySelector('[data-action="close"]').addEventListener("click", closeQuiz);
    announce("Resultado enviado com sucesso.");
    focusHeading();
  }

  document.addEventListener("click", function (event) {
    if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    const trigger = event.target.closest("#reco-cbtn, [data-quiz-entry]");
    if (!trigger) return;
    event.preventDefault();
    openQuiz(trigger);
  });
})();
