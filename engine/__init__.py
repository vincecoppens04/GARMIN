from engine.models.day_record import DayRecord
from engine.models.activity_record import ActivityRecord
from engine.models.user_baselines import UserBaselines
from engine.config import load_env, safe_round

try:
    from engine.orchestrator import process_day
    from engine.connectors.garmin import GarminConnector, get_garmin_client
    from engine.connectors.supabase import SupabaseConnector, get_supabase_client
    from engine.services.notifier import (
        send_phone_notification,
        notify_morning_sync_reminder,
        notify_morning_readiness,
        notify_evening_sync_reminder,
        notify_evening_bedtime,
    )
    from engine.services.ai_coach import AICoach, generate_ai_briefing
except ImportError:
    pass

def calculate_habit_correlations(supabase, user_id: str):
    from datetime import date
    from engine.connectors.supabase import SupabaseConnector
    from engine.calculators.habits import calculate_habit_correlations_from_records
    connector = SupabaseConnector(client=supabase, user_id=user_id)
    history = connector.get_daily_history(date.today().isoformat(), limit=60)
    habits = connector.get_habit_logs(date.today().isoformat(), lookback=60)
    return calculate_habit_correlations_from_records(habits, history)

__all__ = [
    "process_day",
    "DayRecord",
    "ActivityRecord",
    "UserBaselines",
    "GarminConnector",
    "get_garmin_client",
    "SupabaseConnector",
    "get_supabase_client",
    "calculate_habit_correlations",
    "send_phone_notification",
    "notify_morning_sync_reminder",
    "notify_morning_readiness",
    "notify_evening_sync_reminder",
    "notify_evening_bedtime",
    "AICoach",
    "generate_ai_briefing",
    "load_env",
    "safe_round",
]
