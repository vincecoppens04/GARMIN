import time
import httpx
from typing import Optional, Any
from datetime import date, timedelta
from supabase import create_client, Client, ClientOptions
from engine.config import SUPABASE_URL, SUPABASE_ANON_KEY, APP_USER_EMAIL, APP_USER_PASSWORD
from engine.models.day_record import DayRecord
from engine.models.activity_record import ActivityRecord
from engine.models.user_baselines import UserBaselines

class SupabaseConnector:
    """
    Encapsulates authenticated Supabase interactions, baseline loading,
    tiered upserts with schema fallbacks, and multi-day telemetry queries.
    """
    def __init__(self, client: Optional[Client] = None, user_id: Optional[str] = None):
        self.client = client
        self.user_id = user_id

    def authenticate(self, max_retries: int = 3) -> tuple[Client, str]:
        if self.client and self.user_id:
            return self.client, self.user_id

        last_err: Optional[Exception] = None
        for attempt in range(1, max_retries + 1):
            try:
                # Dedicated httpx client with generous 30s read timeout and HTTP/1.1
                # to prevent serverless stream drops and transient ReadTimeout crashes
                custom_http = httpx.Client(
                    timeout=httpx.Timeout(30.0, connect=10.0, read=30.0, write=10.0),
                    http2=False,
                )
                options = ClientOptions(
                    httpx_client=custom_http,
                    postgrest_client_timeout=30.0,
                    storage_client_timeout=30,
                )
                client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY, options=options)
                auth = client.auth.sign_in_with_password({
                    "email": APP_USER_EMAIL,
                    "password": APP_USER_PASSWORD,
                })
                self.client = client
                self.user_id = auth.user.id
                return self.client, self.user_id
            except Exception as e:
                last_err = e
                if attempt < max_retries:
                    wait_sec = attempt * 2.0
                    print(f"  [Supabase Auth Warning] Attempt {attempt}/{max_retries} failed ({type(e).__name__}: {e}). Retrying in {wait_sec:.1f}s...")
                    time.sleep(wait_sec)
                else:
                    print(f"  [Supabase Auth Error] All {max_retries} connection attempts failed: {e}")

        if last_err:
            raise last_err
        raise RuntimeError("Failed to authenticate with Supabase.")

    def get_user_baselines(self) -> UserBaselines:
        client, uid = self.authenticate()
        res = client.table("user_baselines").select("*").eq("user_id", uid).single().execute()
        return UserBaselines.from_supabase_row(res.data or {}, user_id=uid)

    def update_vo2_max(self, vo2_max: float) -> None:
        client, uid = self.authenticate()
        try:
            client.table("user_baselines").update({"vo2_max": vo2_max}).eq("user_id", uid).execute()
        except Exception as e:
            print(f"  [Supabase Warning] Failed to update VO2 max: {e}")

    def get_daily_history(self, target_date: str, limit: int = 60) -> list[dict[str, Any]]:
        client, uid = self.authenticate()
        res = (
            client.table("daily_summaries")
            .select("*")
            .eq("user_id", uid)
            .lt("date", target_date)
            .order("date", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []

    def get_previous_day_summary(self, target_date: str) -> Optional[dict[str, Any]]:
        client, uid = self.authenticate()
        prev_date = (date.fromisoformat(target_date) - timedelta(days=1)).isoformat()
        res = client.table("daily_summaries").select("*").eq("user_id", uid).eq("date", prev_date).execute()
        return res.data[0] if res.data else None

    def get_trailing_activities(self, target_date: str, days: int = 14) -> list[dict[str, Any]]:
        client, uid = self.authenticate()
        cutoff = (date.fromisoformat(target_date) - timedelta(days=days)).isoformat()
        try:
            res = (
                client.table("activities")
                .select("*")
                .eq("user_id", uid)
                .gte("date", cutoff)
                .lte("date", target_date)
                .execute()
            )
            return res.data or []
        except Exception:
            return []

    def get_habit_logs(self, target_date: str, lookback: int = 60) -> list[dict[str, Any]]:
        client, uid = self.authenticate()
        try:
            res = (
                client.table("habit_logs")
                .select("*")
                .eq("user_id", uid)
                .order("date", desc=True)
                .limit(lookback)
                .execute()
            )
            return res.data or []
        except Exception:
            return []

    def get_recent_habit(self, target_date: str) -> Optional[dict[str, Any]]:
        client, uid = self.authenticate()
        prev_date = (date.fromisoformat(target_date) - timedelta(days=1)).isoformat()
        try:
            res = (
                client.table("habit_logs")
                .select("*")
                .eq("user_id", uid)
                .in_("date", [target_date, prev_date])
                .order("date", desc=True)
                .limit(1)
                .execute()
            )
            return res.data[0] if res.data else None
        except Exception:
            return None

    def upsert_day_record(self, record: DayRecord) -> None:
        """
        Upserts DayRecord to Supabase using resilient 3-tier fallback
        to protect against unapplied SQL schema migrations.
        """
        client, _ = self.authenticate()
        # Tier 1: Full V2 record with all columns
        full_dict = record.to_supabase_dict(tier=1)
        try:
            client.table("daily_summaries").upsert(full_dict, on_conflict="user_id,date").execute()
            return
        except Exception as e1:
            err_msg = str(e1)
            print(f"  [Supabase Warning] Tier 1 upsert failed: {err_msg}")

        # Tier 2: Strip unmigrated string columns (recommended_bedtime, sleep_equation_str)
        # but PRESERVE all V2 sports science metrics
        clean_dict = record.to_supabase_dict(tier=2)
        try:
            client.table("daily_summaries").upsert(clean_dict, on_conflict="user_id,date").execute()
            print("  [Supabase Info] Tier 2 upsert succeeded (all V2 metrics saved).")
            return
        except Exception as e2:
            print(f"  [Supabase Warning] Tier 2 upsert deferred: {e2}")

        # Tier 3: Core legacy schema fallback
        safe_dict = record.to_supabase_dict(tier=3)
        client.table("daily_summaries").upsert(safe_dict, on_conflict="user_id,date").execute()
        print("  [Supabase Info] Tier 3 core upsert succeeded.")

    def upsert_activity_record(self, record: ActivityRecord) -> None:
        """Upserts ActivityRecord with fallback if V2 columns not present."""
        client, _ = self.authenticate()
        act_dict = record.to_supabase_dict(include_v2=True)
        try:
            client.table("activities").upsert(act_dict, on_conflict="id").execute()
        except Exception:
            safe_act = record.to_supabase_dict(include_v2=False)
            client.table("activities").upsert(safe_act, on_conflict="id").execute()

def get_supabase_client() -> tuple[Client, str]:
    """Helper preserving standalone function signature."""
    connector = SupabaseConnector()
    return connector.authenticate()
