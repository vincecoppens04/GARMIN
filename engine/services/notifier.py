import os
import json
import urllib.request
from typing import Optional, Any

class NotificationService:
    """
    Manages push notification dispatch via OneSignal REST API, ntfy.sh,
    or generic webhooks to mobile devices.
    """
    @staticmethod
    def send_notification(
        title: str,
        message: str,
        priority: str = "normal",
        tags: Optional[list[str]] = None,
        return_details: bool = False
    ) -> Any:
        delivered = False
        details = {"channel": None, "recipients": 0, "id": None, "errors": None}

        # 1. ntfy.sh (Instant phone push: free iOS/Android app subscribed to your private topic)
        ntfy_topic = os.getenv("NTFY_TOPIC")
        if ntfy_topic:
            try:
                req = urllib.request.Request(
                    f"https://ntfy.sh/{ntfy_topic}",
                    data=message.encode("utf-8"),
                    headers={
                        "Title": title.encode("utf-8"),
                        "Priority": "high" if priority == "high" else "default",
                        "Tags": ",".join(tags) if tags else "running",
                    },
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status == 200:
                        delivered = True
                        details["channel"] = "ntfy"
                        details["recipients"] = 1
                        print(f"  ✓ Push delivered to phone via ntfy.sh ({ntfy_topic})")
            except Exception as e:
                print(f"  [Push Error] ntfy.sh failed: {e}")
                details["errors"] = str(e)

        # 2. OneSignal REST API (Native iOS PWA Web Push directly to phone)
        onesignal_app_id = os.getenv("ONESIGNAL_APP_ID")
        onesignal_api_key = os.getenv("ONESIGNAL_REST_API_KEY") or os.getenv("ONESIGNAL_API_KEY")
        app_url = os.getenv("APP_URL")
        if onesignal_app_id and onesignal_api_key:
            try:
                url = "https://onesignal.com/api/v1/notifications"
                payload = {
                    "app_id": onesignal_app_id,
                    "included_segments": ["Total Subscriptions", "Active Subscriptions", "Subscribed Users"],
                    "headings": {"en": title},
                    "contents": {"en": message},
                }
                if app_url:
                    payload["url"] = app_url
                auth_prefix = "Key" if onesignal_api_key.startswith("os_v2_") else "Basic"
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json; charset=utf-8",
                        "Authorization": f"{auth_prefix} {onesignal_api_key}"
                    },
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    resp_raw = resp.read().decode("utf-8")
                    resp_data = json.loads(resp_raw) if resp_raw else {}
                    recipients = resp_data.get("recipients", 0)
                    errors = resp_data.get("errors")
                    notif_id = resp_data.get("id")
                    details["channel"] = "onesignal"
                    details["id"] = notif_id
                    details["recipients"] = recipients
                    details["errors"] = errors
                    if resp.status == 200 and (recipients > 0 or notif_id):
                        delivered = True
                        print(f"  ✓ Push delivered to iPhone via OneSignal (ID: {notif_id}, recipients: {recipients})")
                    elif errors:
                        print(f"  [OneSignal Notice] {errors}")
            except Exception as e:
                print(f"  [Push Error] OneSignal failed: {e}")
                details["errors"] = str(e)

        # 3. Generic Webhook (Discord / Slack / Pushover / Home Assistant)
        webhook_url = os.getenv("NOTIFY_WEBHOOK_URL")
        if webhook_url:
            try:
                payload = {"title": title, "message": message, "content": f"**{title}**\n{message}"}
                req = urllib.request.Request(
                    webhook_url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status in (200, 204):
                        delivered = True
                        print(f"  ✓ Push delivered to phone via Webhook")
            except Exception as e:
                print(f"  [Push Error] Webhook failed: {e}")

        if return_details:
            return delivered, details
        return delivered

def send_phone_notification(title: str, message: str, priority: str = "normal", tags: list | None = None, return_details: bool = False):
    return NotificationService.send_notification(title, message, priority=priority, tags=tags, return_details=return_details)

def notify_morning_sync_reminder():
    """Notification 1 (07:30): Ask if watch has synced."""
    title = "⌚ Garmin Sync Reminder"
    message = "Hi, have you already uploaded or synced your Garmin?"
    return send_phone_notification(title, message, priority="normal", tags=["watch", "arrows_counterclockwise"])

def notify_morning_readiness(summary: dict[str, Any]):
    """Notification 2 (08:00 or on-demand 'Sync Now'): Daily situation briefing."""
    rec = summary.get("recovery", 50)
    strain = summary.get("strain", 0.0)
    health = summary.get("health_status", "NORMAL")
    alerts = summary.get("health_alerts", [])
    briefing = summary.get("ai_briefing", "")
    t_min = summary.get("target_strain_min", 0.0)
    t_max = summary.get("target_strain_max", 21.0)
    
    if health != "NORMAL" or alerts:
        alert_msg = f"Multiple vital anomalies detected ({', '.join(alerts)}). Cardiovascular strain should be capped today. Rest and active recovery recommended."
        send_phone_notification("⚠️ Health Alert: Rest Recommended", alert_msg, priority="high", tags=["warning", "medical_symbol"])
    
    zone_emoji = "🟢" if rec >= 67 else ("🟡" if rec >= 34 else "🔴")
    title = f"{zone_emoji} Recovery: {rec}% | Daily Situation"
    
    msg_lines = [
        f"Hi, this is your situation for today:",
        f"• Recovery: {rec}% ({'Primed' if rec>=67 else 'Adequate' if rec>=34 else 'Rest Required'})",
        f"• Target Strain: {t_min:.1f} – {t_max:.1f}",
    ]
    if briefing:
        msg_lines.append(f"\"{briefing}\"")
        
    message = "\n".join(msg_lines)
    return send_phone_notification(title, message, priority="normal", tags=["chart_with_upwards_trend", "muscle"])

def notify_evening_sync_reminder():
    """Notification 3 (20:30): Evening sync reminder."""
    title = "⌚ Garmin Evening Sync"
    message = "Hi, have you synced your Garmin recently?"
    return send_phone_notification(title, message, priority="normal", tags=["watch", "bed"])

def notify_evening_bedtime(summary: dict[str, Any]):
    """Notification 4 (21:00): Evening bedtime and wind-down prescription."""
    strain = summary.get("strain", 0.0)
    bedtime = summary.get("bedtime") or summary.get("recommended_bedtime", "22:30")
    need_min = summary.get("sleep_need_min", 435)
    debt = summary.get("debt_min", 0)
    freshness = summary.get("sync_freshness") or (summary.get("metrics_v2") or {}).get("sync_freshness") or {}
    
    need_h = need_min // 60
    need_m = need_min % 60
    
    debt_text = f" (incl. {debt}m debt)" if debt > 0 else ""
    title = f"🌙 Sleep Prescription: Bedtime {bedtime}"
    msg_lines = [
        f"Hi, based on your day strain of {strain:.1f}, target lights-out is {bedtime} to get {need_h}h {need_m:02d}m of sleep{debt_text}."
    ]
    if freshness.get("is_stale"):
        last_t = freshness.get("last_sync_time")
        if last_t:
            msg_lines.append(f"⚠️ Watch not synced since {last_t}. Open Garmin Connect to finalize.")
        else:
            msg_lines.append("⚠️ Watch not synced recently. Open Garmin Connect to finalize.")

    message = "\n".join(msg_lines)
    return send_phone_notification(title, message, priority="normal", tags=["crescent_moon", "sleeping"])
