#%%
import os
import json
from datetime import date, timedelta
from getpass import getpass
from pathlib import Path
from garminconnect import (
    Garmin,
    GarminConnectAuthenticationError,
    GarminConnectConnectionError,
    GarminConnectTooManyRequestsError,
)

# Directory to save token cache
TOKENSTORE = os.path.expanduser("~/.garminconnect")

def load_env(env_path=None):
    """Loads environment variables from .env file without requiring external dependencies."""
    if env_path is None:
        env_path = Path(__file__).resolve().parent / ".env"
    else:
        env_path = Path(env_path)

    if env_path.is_file():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                    val = val[1:-1]
                if key and key not in os.environ:
                    os.environ[key] = val

def init_garmin():
    """Authenticates and caches credentials locally."""
    load_env()
    email = os.getenv("GARMIN_EMAIL") or os.getenv("GARMIN_USERNAME") or os.getenv("EMAIL")
    password = os.getenv("GARMIN_PASSWORD") or os.getenv("PASSWORD")

    token_dir = Path(TOKENSTORE).expanduser()
    token_dir.mkdir(parents=True, exist_ok=True)

    print("Checking for cached Garmin session...")
    try:
        # 1. Attempt to load cached session token
        garmin = Garmin()
        garmin.login(str(token_dir))
        print("Logged in using cached tokens!")
        return garmin
    except Exception:
        # 2. Fall back to manual login if no session exists or token expired
        print("No valid session found. Logging in with credentials...")
        if not email:
            email = input("Garmin Email: ").strip()
        if not password:
            password = getpass("Garmin Password: ").strip()

        garmin = Garmin(
            email=email,
            password=password,
            prompt_mfa=lambda: input("Enter Garmin MFA code: ").strip(),
        )
        garmin.login(str(token_dir))
        try:
            garmin.client.dump(str(token_dir))
        except Exception:
            pass
        print(f"Session saved to {token_dir}")
        return garmin

def dump_sample_data():
    client = init_garmin()
    
    # Let's inspect yesterday's full completed cycle
    target_date = (date.today() - timedelta(days=1)).isoformat()
    print(f"\nFetching data for {target_date}...")

    os.makedirs("sample_dumps", exist_ok=True)

    endpoints = {
        "sleep": lambda: client.get_sleep_data(target_date),
        "hrv": lambda: client.get_hrv_data(target_date),
        "rhr": lambda: client.get_rhr_day(target_date),
        "heart_rates_intraday": lambda: client.get_heart_rates(target_date),
        "stress": lambda: client.get_stress_data(target_date),
        "training_status": lambda: client.get_training_status(target_date),
        "activities": lambda: client.get_activities(0, 5),  # Last 5 workouts
    }

    for name, func in endpoints.items():
        try:
            print(f"-> Pulling {name}...")
            data = func()
            with open(f"sample_dumps/{name}.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"   Saved to sample_dumps/{name}.json")
        except Exception as e:
            print(f"   [Error] Could not fetch {name}: {e}")

if __name__ == "__main__":
    dump_sample_data()
