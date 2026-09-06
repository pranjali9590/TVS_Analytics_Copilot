"""
AI Lending Copilot
-------------------
A domain-grounded assistant for the Residual Value & Risk Analytics app.

Design goals:
1. Every answer is grounded in the SAME numbers the /predict endpoint computes
   (asset health index, risk score, risk band, lending recommendation, etc.)
   rather than being a generic chatbot — so answers stay relevant to what the
   user is actually looking at on the dashboard.
2. Works fully offline / for free, out of the box (pure Python keyword-intent
   matching), so it deploys on Render's free tier with zero extra setup and
   no API key.
3. Optional upgrade path: if an ANTHROPIC_API_KEY environment variable is
   present, harder/open-ended questions that don't match a known intent are
   forwarded to Claude with a strict, grounded system prompt (still anchored
   to the current prediction context) for a more natural-language answer.
   Without a key, those questions get a helpful fallback instead of failing.
"""

import os
import re
import json
import urllib.request
import urllib.error

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

MODEL_FACTS = {
    "algorithm": "Tuned HistGradientBoostingRegressor (Gradient Boosting)",
    "rmse": "Rs. 8,829",
    "mae": "Rs. 6,672",
    "mape": "17.53%",
    "r2": "0.719",
    "classifier_auc": "0.819",
    "top_drivers": [
        "Asset Cost at Disbursal", "Asset Age at Seizure", "Customer Region",
        "OS Balance at Liquidation", "Asset Model", "Asset Health Index",
    ],
}

SUGGESTION_CHIPS_DEFAULT = [
    "Why is this agreement risky?",
    "What does Asset Health Index mean?",
    "How is the recommended LTV calculated?",
    "Which model powers these predictions?",
]

SUGGESTION_CHIPS_WITH_CONTEXT = [
    "Why is this agreement risky?",
    "How can I reduce the risk?",
    "Explain the recommended lending terms",
    "What will this asset be worth in 24 months?",
]


def _num(x, default=None):
    try:
        return float(x)
    except (TypeError, ValueError):
        return default


def _fmt_currency(x):
    v = _num(x)
    if v is None:
        return "N/A"
    return f"Rs. {v:,.0f}"


def _extract(context, *path):
    node = context or {}
    for p in path:
        if not isinstance(node, dict) or p not in node:
            return None
        node = node[p]
    return node


def _has_context(context):
    return isinstance(context, dict) and "summary" in context


def _contains_any(text, words):
    for w in words:
        if re.search(r'\b' + re.escape(w) + r'\b', text):
            return True
    return False


def _contains_all(text, words):
    return all(re.search(r'\b' + re.escape(w) + r'\b', text) for w in words)


# ---------------------------------------------------------------- intents

def _intent_greeting(q, ctx):
    if _contains_any(q, ["hi", "hello", "hey", "namaste"]) and len(q.split()) <= 4:
        return ("Hi! I'm the AI Lending Copilot for this dashboard. I can explain any "
                "prediction, risk score, or recommended lending terms in plain language — "
                "just ask, or tap a suggestion below.")
    return None


def _intent_capabilities(q, ctx):
    if _contains_any(q, ["what can you do", "help", "capabilities", "how do you work", "what are you"]):
        return ("I can help you understand this dashboard's output:\n"
                "\u2022 Explain the residual value forecast and risk score/band for the agreement you just entered\n"
                "\u2022 Break down Asset Health Index, Market Volatility, Segment Risk, Recovery Efficiency and Profitability\n"
                "\u2022 Explain why the LTV, pricing (rate) and tenure recommendations came out the way they did\n"
                "\u2022 Explain the 12/24/36-month scenario forecasts\n"
                "\u2022 Tell you which ML model powers the predictions and how accurate it is\n\n"
                "Run a prediction first for the most specific answers — I'll reference your actual numbers.")
    return None


def _intent_risk_score_def(q, ctx):
    if _contains_any(q, ["risk score"]) and _contains_any(q, ["what", "mean", "how is", "explain", "definition", "calculat"]):
        base = ("The Residual Risk Score (0\u2013100) is the % of the original asset cost the model "
                "expects to be LOST at liquidation: score = 100 \u00d7 (1 \u2212 predicted value / asset cost). "
                "0 = no expected loss, 100 = total loss.")
        if _has_context(ctx):
            score = _extract(ctx, "summary", "residual_risk_score")
            band = _extract(ctx, "summary", "risk_band")
            base += f"\n\nFor your current agreement: score = {score}, which falls in the **{band}** band."
        return base
    return None


def _intent_risk_band_def(q, ctx):
    if _contains_any(q, ["risk band", "low medium high critical", "risk categor", "what bands"]):
        return ("Risk scores are bucketed into 4 bands:\n"
                "\u2022 0\u201325 \u2192 LOW\n\u2022 26\u201350 \u2192 MEDIUM\n\u2022 51\u201375 \u2192 HIGH\n\u2022 76\u2013100 \u2192 CRITICAL\n\n"
                "HIGH/CRITICAL agreements automatically get tighter recommended LTV, higher pricing and shorter tenure.")
    return None


def _intent_why_risk(q, ctx):
    if _contains_any(q, ["why is this", "why is it", "why risky", "why high", "why critical", "why so risky",
                          "reason for risk", "why does it show"]) and _contains_any(q, ["risk", "risky", "critical", "high"]):
        if not _has_context(ctx):
            return ("Run a prediction first (fill in the agreement form and click Analyze) — "
                    "then ask me again and I'll explain exactly why *that* agreement scored the way it did.")
        band = _extract(ctx, "summary", "risk_band")
        score = _extract(ctx, "summary", "residual_risk_score")
        ahi = _extract(ctx, "asset_analytics", "asset_health_index")
        mvs = _extract(ctx, "asset_analytics", "market_volatility_score")
        seg = _extract(ctx, "asset_analytics", "segment_risk_index")
        pred = _extract(ctx, "summary", "predicted_sold_amount")
        lines = [f"This agreement scored **{score}/100 ({band})**. Main contributors, based on your inputs:"]
        if ahi is not None:
            tag = "weak" if ahi < 2 else ("moderate" if ahi < 2.7 else "good")
            lines.append(f"\u2022 Asset Health Index = {ahi} ({tag} condition) \u2014 lower condition scores pull the forecast value down.")
        if mvs is not None:
            tag = "elevated" if mvs >= 30 else "typical"
            lines.append(f"\u2022 Market Volatility Score = {mvs} ({tag}) \u2014 EVs and more recent seizures score higher here.")
        if seg is not None:
            tag = "above-average" if seg > 0 else "below-average"
            lines.append(f"\u2022 Segment Risk Index = {seg} \u2014 this asset model has {tag} resale risk vs. the overall book.")
        lines.append(f"\u2022 Predicted sale value = {_fmt_currency(pred)} vs. the original asset cost you entered.")
        return "\n".join(lines)
    return None


def _intent_reduce_risk(q, ctx):
    reduce_words = ["reduce", "lower", "minimize", "manage", "improve", "decrease"]
    if _contains_any(q, reduce_words) and _contains_any(q, ["risk", "risky"]):
        base = ("Levers that most directly reduce residual risk on future agreements:\n"
                "\u2022 Prefer well-maintained assets (higher Asset Health Index \u2014 no accident history, good body/tyre/engine condition)\n"
                "\u2022 Cap LTV lower for older assets or asset models with a high Segment Risk Index\n"
                "\u2022 Shorten tenure for EVs or assets in fast-depreciating segments (reduces exposure at the point of highest depreciation)\n"
                "\u2022 Price (rate) up modestly for HIGH/CRITICAL band agreements to compensate for expected loss")
        if _has_context(ctx):
            band = _extract(ctx, "summary", "risk_band")
            action = _extract(ctx, "business_decision", "recommended_action")
            if band and action:
                base += f"\n\nFor this specific agreement ({band} band), the engine's recommendation is: \u201c{action}\u201d"
        return base
    return None


def _intent_asset_health(q, ctx):
    if _contains_any(q, ["asset health index", "asset health"]):
        base = ("Asset Health Index is the average of 4 condition grades (body, tyre, general, engine "
                "\u2014 each scored Good=3 / Average=2 / Poor=1), with a 0.5-point penalty if the asset "
                "has an accident history. Range: roughly 0.5 to 3.0, higher = better condition.")
        v = _extract(ctx, "asset_analytics", "asset_health_index")
        if v is not None:
            base += f"\n\nYour current agreement: {v} / 3.0"
        return base
    return None


def _intent_market_volatility(q, ctx):
    if _contains_any(q, ["market volatility"]):
        base = ("Market Volatility Score reflects how exposed an asset is to market disruption: EVs "
                "start at a higher base score than petrol vehicles (EV resale markets are younger and "
                "less stable), plus a penalty for more recent seizure years.")
        v = _extract(ctx, "asset_analytics", "market_volatility_score")
        if v is not None:
            base += f"\n\nYour current agreement: {v} / 100"
        return base
    return None


def _intent_segment_risk(q, ctx):
    if _contains_any(q, ["segment risk"]):
        base = ("Segment Risk Index compares this asset model's average historical resale ratio to the "
                "overall book's average. Positive = this model resells worse than average (higher risk); "
                "negative = it resells better than average.")
        v = _extract(ctx, "asset_analytics", "segment_risk_index")
        if v is not None:
            base += f"\n\nYour current agreement: {v}"
        return base
    return None


def _intent_recovery_efficiency(q, ctx):
    if _contains_any(q, ["recovery efficiency"]):
        base = ("Recovery Efficiency = predicted sale value \u00f7 outstanding balance at liquidation, as a %. "
                "Above 100% means the expected recovery fully covers the outstanding loan balance; below "
                "100% implies a shortfall.")
        v = _extract(ctx, "asset_analytics", "estimated_recovery_efficiency")
        if v is not None:
            base += f"\n\nYour current agreement: {v}%"
        return base
    return None


def _intent_profitability(q, ctx):
    if _contains_any(q, ["profitability", "profit"]):
        base = "Estimated Profitability = predicted sale value \u2212 outstanding balance at liquidation, in Rs."
        v = _extract(ctx, "asset_analytics", "estimated_profitability")
        if v is not None:
            base += f"\n\nYour current agreement: {_fmt_currency(v)}"
        return base
    return None


def _intent_ltv(q, ctx):
    if _contains_any(q, ["ltv", "loan to value", "loan-to-value"]):
        base = ("Recommended LTV = current LTV \u00d7 (1 \u2212 0.18 \u00d7 risk_factor), where risk_factor = "
                "risk score / 100 \u2014 so higher-risk agreements get a proportionally lower LTV, "
                "clipped between 40% and 95%.")
        cur = _extract(ctx, "lending_recommendation", "current_ltv")
        rec = _extract(ctx, "lending_recommendation", "recommended_ltv")
        if cur is not None and rec is not None:
            base += f"\n\nYour current agreement: {cur}% \u2192 recommended {rec}%"
        return base
    return None


def _intent_pricing(q, ctx):
    if _contains_any(q, ["pricing", "interest rate", "net irr", "rate of interest", "irr"]):
        base = ("Recommended pricing (rate) = current rate \u00d7 (1 + 0.12 \u00d7 risk_factor) \u2014 riskier "
                "agreements are priced slightly higher to compensate for expected residual loss.")
        cur = _extract(ctx, "lending_recommendation", "current_pricing")
        rec = _extract(ctx, "lending_recommendation", "recommended_pricing")
        if cur is not None and rec is not None:
            base += f"\n\nYour current agreement: {cur}% \u2192 recommended {rec}%"
        return base
    return None


def _intent_tenure(q, ctx):
    if _contains_any(q, ["tenure"]):
        base = ("Recommended tenure = current tenure \u00d7 (1 \u2212 0.30 \u00d7 risk_factor), floored at 12 "
                "months \u2014 shortening exposure time for riskier agreements.")
        cur = _extract(ctx, "lending_recommendation", "current_tenure")
        rec = _extract(ctx, "lending_recommendation", "recommended_tenure")
        if cur is not None and rec is not None:
            base += f"\n\nYour current agreement: {cur} months \u2192 recommended {rec} months"
        return base
    return None


def _intent_model_info(q, ctx):
    if _contains_any(q, ["which model", "what model", "algorithm", "accuracy", "mape", "rmse",
                          "how accurate", "r2", "r-squared", "r\u00b2", "auc"]):
        return (f"Predictions come from a {MODEL_FACTS['algorithm']}, selected after benchmarking "
                f"against Ridge Regression and Random Forest.\n\n"
                f"Test-set performance: RMSE = {MODEL_FACTS['rmse']}, MAE = {MODEL_FACTS['mae']}, "
                f"MAPE = {MODEL_FACTS['mape']}, R\u00b2 = {MODEL_FACTS['r2']}.\n"
                f"A companion High-Risk classifier reaches AUC-ROC = {MODEL_FACTS['classifier_auc']}.\n\n"
                f"Top global drivers of the forecast: {', '.join(MODEL_FACTS['top_drivers'][:4])}.")
    return None


def _intent_scenario(q, ctx):
    month_pattern = re.search(r"\d+\s*-?\s*months?", q) is not None
    if month_pattern or _contains_any(q, ["ev adoption", "inflation", "fuel price", "scenario",
                                           "future value", "forecast", "worth in the future"]):
        base = ("The Scenario Simulator projects residual value forward 12/24/36 months, adjusting the "
                "base depreciation curve for EV-adoption pressure, inflation, and fuel-price shocks "
                "(petrol assets are hit hardest by EV-adoption and fuel-price stress; EVs are relatively "
                "more exposed to inflation on replacement parts).")
        f12 = _extract(ctx, "forecast", "forecast_12_month")
        f24 = _extract(ctx, "forecast", "forecast_24_month")
        f36 = _extract(ctx, "forecast", "forecast_36_month")
        if f12 is not None:
            base += (f"\n\nYour current agreement's base-case forecast: "
                      f"12m = {_fmt_currency(f12)}, 24m = {_fmt_currency(f24)}, 36m = {_fmt_currency(f36)}.")
        return base
    return None


def _intent_drivers(q, ctx):
    if _contains_any(q, ["important feature", "important features", "top driver", "top drivers",
                          "top factor", "top factors", "what drives", "what influences",
                          "feature importance", "most important"]):
        return ("Across the full test set, the strongest drivers of predicted residual value are (in "
                "order): " + ", ".join(MODEL_FACTS["top_drivers"]) + ". These were confirmed with both "
                "impurity-based and permutation-importance techniques.")
    return None


def _intent_thanks(q, ctx):
    if _contains_any(q, ["thank", "thanks", "thx", "great", "awesome", "cool"]) and len(q.split()) <= 6:
        return "You're welcome! Ask me anything else about this prediction or the model."
    return None


INTENTS = [
    _intent_greeting, _intent_thanks, _intent_capabilities,
    _intent_why_risk, _intent_reduce_risk,
    _intent_risk_score_def, _intent_risk_band_def,
    _intent_asset_health, _intent_market_volatility, _intent_segment_risk,
    _intent_recovery_efficiency, _intent_profitability,
    _intent_ltv, _intent_pricing, _intent_tenure,
    _intent_model_info, _intent_scenario, _intent_drivers,
]


# ---------------------------------------------------------------- optional LLM fallback

def _llm_fallback(question, context):
    if not ANTHROPIC_API_KEY:
        return None

    context_str = json.dumps(context, indent=2) if context else "No prediction has been run yet."

    system_prompt = (
        "You are the AI Lending Copilot embedded in a residual-value & lending-risk dashboard for "
        "two-wheeler asset financing (TVS Credit). Answer ONLY questions about: this dashboard, the "
        "current prediction/context JSON provided, residual value forecasting, lending risk, LTV/"
        "pricing/tenure recommendations, or the underlying ML model. Be concise (under 120 words), "
        "business-friendly, and ground any numbers you cite in the provided context JSON \u2014 never "
        "invent figures that aren't in it. If the question is unrelated to lending/residual-value "
        "analytics, politely say so and redirect to what you can help with.\n\n"
        f"Current prediction context:\n{context_str}"
    )

    body = json.dumps({
        "model": ANTHROPIC_MODEL,
        "max_tokens": 300,
        "system": system_prompt,
        "messages": [{"role": "user", "content": question}],
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        parts = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
        text = "\n".join(p for p in parts if p).strip()
        return text or None
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, KeyError):
        return None


def _fallback_answer(context):
    if _has_context(context):
        return ("I don't have a scripted answer for that yet, but here's what I can tell you about your "
                "current agreement: risk band **" + str(_extract(context, "summary", "risk_band")) +
                "**, recommended action: \u201c" + str(_extract(context, "business_decision", "recommended_action")) +
                "\u201d. Try asking about risk score, asset health index, LTV, pricing, tenure, the model, "
                "or scenario forecasts.")
    return ("I don't have a scripted answer for that yet. I can reliably help with: residual risk score "
            "and bands, Asset Health / Market Volatility / Segment Risk / Recovery Efficiency / "
            "Profitability, LTV / pricing / tenure recommendations, the ML model and its accuracy, and "
            "the EV/inflation/fuel-price scenario forecasts. Run a prediction first for the most "
            "specific answers.")


def answer_question(question, context=None):
    """Main entry point. Returns {"answer": str, "suggestions": [str, ...], "source": str}."""
    q = (question or "").strip().lower()
    if not q:
        return {
            "answer": "Ask me anything about this dashboard's predictions, risk scores, or lending recommendations.",
            "suggestions": SUGGESTION_CHIPS_WITH_CONTEXT if _has_context(context) else SUGGESTION_CHIPS_DEFAULT,
            "source": "rules",
        }

    for intent_fn in INTENTS:
        answer = intent_fn(q, context)
        if answer:
            return {
                "answer": answer,
                "suggestions": SUGGESTION_CHIPS_WITH_CONTEXT if _has_context(context) else SUGGESTION_CHIPS_DEFAULT,
                "source": "rules",
            }

    llm_answer = _llm_fallback(question, context)
    if llm_answer:
        return {
            "answer": llm_answer,
            "suggestions": SUGGESTION_CHIPS_WITH_CONTEXT if _has_context(context) else SUGGESTION_CHIPS_DEFAULT,
            "source": "llm",
        }

    return {
        "answer": _fallback_answer(context),
        "suggestions": SUGGESTION_CHIPS_WITH_CONTEXT if _has_context(context) else SUGGESTION_CHIPS_DEFAULT,
        "source": "fallback",
    }
