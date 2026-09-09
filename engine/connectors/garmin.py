import os
from pathlib import Path
from typing import Optional, Any
from garminconnect import Garmin
from engine.config import TOKENSTORE

class GarminConnector:
    """
    Encapsulates Garmin Connect API client management, OAuth session token caching,
    and robust endpoint extraction.
    """
    def __init__(self, tokenstore_path: Optional[str] = None):
        self.tokenstore_path = tokenstore_path or TOKENSTORE
        self.client: Optional[Garmin] = None

    def get_client(self) -> Garmin:
        if self.client is not None:
            return self.client

        token_dir = Path(self.tokenstore_path).expanduser()
        token_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Try to reuse cached OAuth tokens (prevents security re-login emails)
        try:
            garmin = Garmin()
            garmin.login(str(token_dir))
            print("✓ Authenticated using cached Garmin session tokens.")
            self.client = garmin
            return garmin
        except Exception as e:
            print(f"[Notice] Cached session missing or expired ({e}). Logging in with credentials...")

        # 2. Fallback: Full login with credentials
        email = os.getenv("GARMIN_EMAIL") or os.getenv("EMAIL")
        password = os.getenv("GARMIN_PASSWORD") or os.getenv("PASSWORD")
        
        garmin = Garmin(
            email=email,
            password=password,
            prompt_mfa=lambda: input("Enter Garmin MFA code: ").strip(),
        )
        garmin.login(str(token_dir))

        # 3. Save tokens so subsequent syncs reuse them
        try:
            if hasattr(garmin, "client") and hasattr(garmin.client, "dump"):
                garmin.client.dump(str(token_dir))
            elif hasattr(garmin, "garth") and hasattr(garmin.garth, "dump"):
                garmin.garth.dump(str(token_dir))
            elif hasattr(garmin, "dump"):
                garmin.dump(str(token_dir))
            print(f"✓ Session tokens successfully saved to {token_dir}")
        except Exception as dump_err:
            print(f"[Warning] Failed to persist session tokens: {dump_err}")

        self.client = garmin
        return garmin

    def fetch_day_raw_data(self, target_date: str) -> dict[str, Any]:
        """Fetches all primary telemetry endpoints from Garmin for the given day."""
        client = self.get_client()
        
        sleep_raw = {}
        try:
            sleep_raw = client.get_sleep_data(target_date) or {}
        except Exception as e:
            print(f"  [Garmin Warning] Sleep endpoint fetch error: {e}")

        hrv_raw = {}
        try:
            hrv_raw = client.get_hrv_data(target_date) or {}
        except Exception as e:
            print(f"  [Garmin Warning] HRV endpoint fetch error: {e}")

        hr_raw = {}
        try:
            hr_raw = client.get_heart_rates(target_date) or {}
        except Exception as e:
            print(f"  [Garmin Warning] Heart rates endpoint fetch error: {e}")

        rhr_raw = None
        try:
            rhr_raw = client.get_rhr_day(target_date)
        except Exception as e:
            print(f"  [Garmin Warning] RHR day endpoint fetch error: {e}")

        stress_raw = None
        try:
            stress_raw = client.get_all_day_stress(target_date)
        except Exception:
            try:
                stress_raw = client.get_stress_data(target_date)
            except Exception:
                pass

        activities = []
        try:
            activities = client.get_activities_by_date(target_date, target_date) or []
        except Exception as e:
            print(f"  [Garmin Warning] Activities endpoint fetch error: {e}")

        training_status = None
        try:
            training_status = client.get_training_status(target_date)
        except Exception:
            pass

        return {
            "sleep_raw": sleep_raw,
            "hrv_raw": hrv_raw,
            "hr_raw": hr_raw,
            "rhr_raw": rhr_raw,
            "stress_raw": stress_raw,
            "activities": activities,
            "training_status": training_status,
        }

def get_garmin_client() -> Garmin:
    """Helper preserving standalone function signature."""
    connector = GarminConnector()
    return connector.get_client()
