import os
import json
import urllib.request
from typing import Any

class AICoach:
    """
    Generates intelligent, clinical sports science briefings.
    Prefers Google Gemini 2.0 Flash if GEMINI_API_KEY is available in environment,
    with an offline deterministic rule engine fallback.
    """
    @staticmethod
    def generate_briefing(
        recovery_score: int,
        day_strain: float,
        target_strain_min: float,
        target_strain_max: float,
        current_debt: int,
        health_status: str,
        alerts: list[str],
        driver: str,
    ) -> str:
        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"
                alert_str = ", ".join(alerts) if alerts else "None"
                prompt = (
                    f"You are an elite sports scientist and physiologist. Analyze this morning's telemetry:\n"
                    f"- Recovery Score: {recovery_score}%\n"
                    f"- Primary Driver: {driver}\n"
                    f"- Health Status: {health_status}\n"
                    f"- Health Alerts: {alert_str}\n"
                    f"- Prescribed Day Strain Target: {target_strain_min:.1f} - {target_strain_max:.1f} / 21.0\n"
                    f"- Acute Sleep Debt: {current_debt} min\n"
                    f"Write exactly 2 concise, clinical, and directly actionable sentences for the athlete's morning briefing. "
                    f"No conversational filler, no greetings, no hashtags. Focus on capacity to absorb cardiovascular load and bedtime strategy."
                )
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": 90, "temperature": 0.4}
                }
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=4) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    if text:
                        return text
            except Exception:
                pass  # Seamless fallback to local deterministic rule engine

        # --- Local Deterministic Sports Science Rule Engine ---
        if health_status == "HIGH_STRAIN_SICKNESS":
            return (
                "CRITICAL HEALTH ALERT: Multiple vital anomalies indicate acute systemic stress or early infection. "
                "Suspend all cardiovascular exertion today, prioritize hydration, and focus entirely on passive recovery."
            )
        if health_status == "WATCH":
            alerts_joined = ", ".join(alerts)
            alert_text = f" ({alerts_joined})" if alerts else ""
            return (
                f"PHYSIOLOGICAL STRAIN ELEVATED: Vitals show significant deviation from your 30-day baseline{alert_text}. "
                f"Cap exertion at gentle active recovery (under {target_strain_max:.1f} strain) and avoid strenuous cardio."
            )

        if recovery_score >= 67:
            if current_debt > 30:
                return (
                    f"Autonomic recovery is primed ({driver}) despite {current_debt}m of acute sleep debt. "
                    f"You have capacity to absorb {target_strain_min:.1f}–{target_strain_max:.1f} strain today, but prioritize an earlier bedtime tonight to clear the deficit."
                )
            return (
                f"Parasympathetic tone is optimal ({driver}), indicating high cardiovascular adaptability. "
                f"You are greenlit for strenuous training—target {target_strain_min:.1f}–{target_strain_max:.1f} strain today."
            )
        elif recovery_score >= 34:
            if recovery_score >= 50:
                return (
                    f"Physiological equilibrium is steady ({driver}). "
                    f"Your cardiovascular system is prepared for moderate maintenance load; target {target_strain_min:.1f}–{target_strain_max:.1f} strain today."
                )
            return (
                f"Mild systemic fatigue detected ({driver}). "
                f"Modulate today's training volume to avoid overreaching—cap strain at {target_strain_max:.1f} and prioritize restorative nutrition."
            )
        else:
            return (
                f"Autonomic recovery is suppressed ({driver}). "
                f"Cardiovascular reserve is restricted today; limit exertion to gentle active recovery (under {target_strain_max:.1f} strain) to restore balance."
            )

def generate_ai_briefing(
    recovery_score: int,
    day_strain: float,
    target_strain_min: float,
    target_strain_max: float,
    current_debt: int,
    health_status: str,
    alerts: list[str],
    driver: str,
) -> str:
    """Helper preserving standalone function signature."""
    return AICoach.generate_briefing(
        recovery_score=recovery_score,
        day_strain=day_strain,
        target_strain_min=target_strain_min,
        target_strain_max=target_strain_max,
        current_debt=current_debt,
        health_status=health_status,
        alerts=alerts,
        driver=driver,
    )
