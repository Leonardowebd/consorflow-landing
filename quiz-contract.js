(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  if (root) root.ConsorflowQuizContract = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const QUIZ_VERSION = "consorflow-icp-v1.0";
  const EVENT_NAME = "landing_quiz_completed";
  const PRIVACY_NOTICE_VERSION = "landing-quiz-privacy-v1.0";

  const QUESTIONS = [
    {
      field: "papel_operacao",
      question: "Qual é o seu papel hoje?",
      options: [
        ["owner_partner", "Dono ou sócio de escritório de consórcio", 15],
        ["sales_manager_decider", "Gestor comercial com poder de decisão", 12],
        ["independent_broker", "Corretor autônomo", 10],
        ["seller_non_decider", "Vendedor sem poder de decisão", 4],
        ["outside_consortium_sales", "Não atuo com venda de consórcio", 0]
      ]
    },
    {
      field: "nivel_operacao",
      question: "Em que nível está a operação?",
      options: [
        ["starting", "Estruturando a operação agora", 3],
        ["manual", "Operando, mas de forma manual", 8],
        ["structured_low_automation", "Processo definido, pouca automação", 10],
        ["scaling_with_bottlenecks", "Operação em crescimento, com gargalos", 10],
        ["automated_predictable", "Operação automatizada e previsível", 6]
      ]
    },
    {
      field: "tamanho_equipe_vendas",
      question: "Quantas pessoas vendem hoje?",
      options: [
        ["1", "Só eu", 4],
        ["2", "2 pessoas", 6],
        ["3_5", "3 a 5", 8],
        ["6_10", "6 a 10", 10],
        ["11_15", "11 a 15", 10],
        ["16_plus", "16 ou mais", 8]
      ]
    },
    {
      field: "faixa_faturamento_mensal",
      question: "Qual é a faixa de faturamento mensal da operação?",
      financial: true,
      options: [
        ["up_to_20k", "Até R$ 20 mil", 2],
        ["20k_50k", "De R$ 20 mil a R$ 50 mil", 4],
        ["50k_100k", "De R$ 50 mil a R$ 100 mil", 6],
        ["100k_250k", "De R$ 100 mil a R$ 250 mil", 8],
        ["above_250k", "Acima de R$ 250 mil", 10],
        ["not_disclosed", "Prefiro não informar", 5]
      ]
    },
    {
      field: "lucro_mensal_20k",
      question: "Hoje, o lucro mensal fica acima de R$ 20 mil?",
      financial: true,
      options: [
        ["above", "Sim", 10],
        ["below", "Não", 4],
        ["break_even_or_loss", "Estamos no ponto de equilíbrio ou com prejuízo", 1],
        ["not_disclosed", "Prefiro não informar", 5]
      ]
    },
    {
      field: "maturidade_processo",
      question: "Como os leads são conduzidos hoje?",
      options: [
        ["individual_unstructured", "Cada vendedor conduz do seu jeito", 8],
        ["defined_manual", "Existe um fluxo, mas o controle é manual", 10],
        ["crm_low_adoption", "Usamos CRM, com baixa adesão ou dados incompletos", 10],
        ["crm_needs_automation", "CRM e rotina funcionam, falta automação", 9],
        ["automated_measured", "Processo automatizado, medido e revisado", 5]
      ]
    },
    {
      field: "volume_leads_mensal",
      question: "Quantos leads novos entram por mês?",
      options: [
        ["under_30", "Menos de 30", 2],
        ["30_99", "30 a 99", 5],
        ["100_299", "100 a 299", 8],
        ["300_999", "300 a 999", 10],
        ["1000_plus", "1.000 ou mais", 8],
        ["unknown", "Não sei", 4]
      ]
    },
    {
      field: "principal_gargalo",
      question: "Qual é o principal gargalo?",
      options: [
        ["slow_first_response", "Demora na primeira resposta", 0],
        ["unqualified_leads", "Leads sem qualificação", 0],
        ["inconsistent_followup", "Follow-up inconsistente", 0],
        ["pipeline_visibility", "Falta de visão do pipeline", 0],
        ["low_process_adoption", "Baixa adesão do time ao processo", 0],
        ["other", "Outro", 0]
      ]
    },
    {
      field: "urgencia_implantacao",
      question: "Quando você quer resolver isso?",
      options: [
        ["now", "Agora", 10],
        ["within_30_days", "Nos próximos 30 dias", 8],
        ["this_quarter", "Neste trimestre", 5],
        ["researching", "Estou apenas avaliando", 2]
      ]
    },
    {
      field: "capacidade_decisao",
      question: "Como a decisão de compra acontece?",
      options: [
        ["sole_decider", "Eu decido", 15],
        ["joint_decider", "Decido com sócio ou diretoria", 12],
        ["influencer", "Eu recomendo, outra pessoa aprova", 6],
        ["no_influence", "Não participo da decisão", 1]
      ]
    }
  ].map(function (question) {
    return Object.freeze({
      ...question,
      options: Object.freeze(question.options.map(function (option) {
        return Object.freeze({ value: option[0], label: option[1], points: option[2] });
      }))
    });
  });

  const FIELD_NAMES = Object.freeze(QUESTIONS.map(function (question) { return question.field; }));
  const FINANCIAL_FIELDS = Object.freeze(["faixa_faturamento_mensal", "lucro_mensal_20k"]);
  const BANDS = Object.freeze(["priority", "good_fit", "nurture", "low_fit"]);
  const GARGALO_LABELS = Object.freeze(Object.fromEntries(
    QUESTIONS[7].options.map(function (option) { return [option.value, option.label]; })
  ));

  const RESULTS = Object.freeze({
    priority: Object.freeze({
      label: "Prioridade",
      title: "Sua operação tem prioridade de diagnóstico.",
      message: "Há volume, urgência e espaço claro para organizar qualificação e follow-up.",
      primaryCta: "Agendar diagnóstico",
      secondaryCta: "Receber resumo no WhatsApp"
    }),
    good_fit: Object.freeze({
      label: "Bom encaixe",
      title: "Existe um bom encaixe operacional.",
      message: "Seu processo já tem tração. O próximo passo é localizar onde os leads perdem ritmo.",
      primaryCta: "Ver diagnóstico recomendado",
      secondaryCta: "Falar com um especialista"
    }),
    nurture: Object.freeze({
      label: "Em estruturação",
      title: "Seu próximo ganho vem de processo.",
      message: "Antes de automatizar mais, vale padronizar entrada, qualificação e follow-up.",
      primaryCta: "Receber checklist de operação",
      secondaryCta: "Conhecer a Consorflow"
    }),
    low_fit: Object.freeze({
      label: "Baixa aderência",
      title: "Talvez este não seja o momento certo.",
      message: "Preparamos um material curto para organizar os próximos passos sem compromisso.",
      primaryCta: "Acessar guia prático",
      secondaryCta: ""
    })
  });

  function optionFor(field, value) {
    const question = QUESTIONS.find(function (item) { return item.field === field; });
    return question && question.options.find(function (option) { return option.value === value; });
  }

  function baseBand(score) {
    if (score >= 75) return "priority";
    if (score >= 50) return "good_fit";
    if (score >= 30) return "nurture";
    return "low_fit";
  }

  function scoreAnswers(answers) {
    const safeAnswers = answers || {};
    let scoreTotal = 0;
    QUESTIONS.forEach(function (question) {
      const option = optionFor(question.field, safeAnswers[question.field]);
      if (option) scoreTotal += option.points;
    });

    const nonIcp = safeAnswers.papel_operacao === "outside_consortium_sales";
    let scoreBand = baseBand(scoreTotal);
    if (nonIcp) scoreBand = "low_fit";
    else if (safeAnswers.capacidade_decisao === "no_influence" && scoreBand === "priority") scoreBand = "good_fit";

    return Object.freeze({ score_total: scoreTotal, score_band: scoreBand, non_icp: nonIcp });
  }

  function validateAnswers(answers) {
    const errors = [];
    const input = answers && typeof answers === "object" ? answers : {};
    FIELD_NAMES.forEach(function (field) {
      if (!optionFor(field, input[field])) errors.push(field);
    });
    return errors;
  }

  function qualificationFromAnswers(answers) {
    const errors = validateAnswers(answers);
    if (errors.length) throw new Error("Respostas inválidas: " + errors.join(", "));
    return Object.freeze({ ...scoreAnswers(answers), ...Object.fromEntries(FIELD_NAMES.map(function (field) {
      return [field, answers[field]];
    })) });
  }

  const ANALYTICS_ALLOWLIST = Object.freeze({
    quiz_started: Object.freeze(["quiz_version", "entry_point", "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"]),
    quiz_step_completed: Object.freeze(["quiz_version", "step_number", "question_id"]),
    quiz_completed: Object.freeze(["quiz_version", "score_band", "non_icp"]),
    quiz_result_cta_clicked: Object.freeze(["quiz_version", "score_band", "cta_id"]),
    quiz_lead_submitted: Object.freeze(["quiz_version", "score_band", "commercial_contact"])
  });

  function safeAnalyticsValue(key, value) {
    if (key === "quiz_version") return QUIZ_VERSION;
    if (key === "score_band") return BANDS.includes(value) ? value : undefined;
    if (key === "non_icp" || key === "commercial_contact") return typeof value === "boolean" ? value : undefined;
    if (key === "step_number") return Number.isInteger(value) && value >= 1 && value <= 10 ? value : undefined;
    if (key === "question_id") return FIELD_NAMES.includes(value) ? value : undefined;
    if (key === "entry_point" || key === "cta_id") {
      return typeof value === "string" && /^[a-z0-9_:-]{1,80}$/.test(value) ? value : undefined;
    }
    if (key.startsWith("utm_")) {
      if (typeof value !== "string" || value.length > 120) return undefined;
      if (/[\w.+-]+@[\w.-]+\.[a-z]{2,}/i.test(value) || /(?:\d[\s().+-]*){10,}/.test(value)) return undefined;
      return value;
    }
    return undefined;
  }

  function sanitizeAnalyticsEvent(eventName, properties) {
    const allowed = ANALYTICS_ALLOWLIST[eventName];
    if (!allowed) return null;
    const safe = { event: eventName };
    allowed.forEach(function (key) {
      if (!properties || !Object.prototype.hasOwnProperty.call(properties, key)) return;
      const value = safeAnalyticsValue(key, properties[key]);
      if (value !== undefined) safe[key] = value;
    });
    safe.quiz_version = QUIZ_VERSION;
    return Object.freeze(safe);
  }

  return Object.freeze({
    ANALYTICS_ALLOWLIST,
    BANDS,
    EVENT_NAME,
    FIELD_NAMES,
    FINANCIAL_FIELDS,
    GARGALO_LABELS,
    PRIVACY_NOTICE_VERSION,
    QUESTIONS: Object.freeze(QUESTIONS),
    QUIZ_VERSION,
    RESULTS,
    baseBand,
    optionFor,
    qualificationFromAnswers,
    sanitizeAnalyticsEvent,
    scoreAnswers,
    validateAnswers
  });
});
