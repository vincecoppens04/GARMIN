import os
from pathlib import Path

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

load_env()
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
APP_USER_EMAIL = os.getenv("APP_USER_EMAIL")
APP_USER_PASSWORD = os.getenv("APP_USER_PASSWORD")

def run():
    print("1. Initializing Supabase client with anon key...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

    print(f"2. Authenticating as {APP_USER_EMAIL}...")
    auth_response = supabase.auth.sign_in_with_password({
        "email": APP_USER_EMAIL,
        "password": APP_USER_PASSWORD,
    })

    user_id = auth_response.user.id
    print(f"   Authenticated! User UUID: {user_id}")

    # 3. Read user baselines (proves SELECT policy works)
    print("\n3. Testing SELECT policy on user_baselines...")
    baselines = supabase.table("user_baselines").select("*").eq("user_id", user_id).execute()
    print("   User Baselines from DB:", baselines.data)

    # 4. Insert/Upsert a test daily summary (proves INSERT/UPDATE policy works)
    print("\n4. Testing UPSERT on daily_summaries...")
    test_row = {
        "user_id": user_id,
        "date": "2026-09-02",
        "recovery_score": 84,
        "recovery_driver": "HRV optimal (+14%) | RHR stable",
        "day_strain": 10.2,
        "hrv_rmssd": 64.0,
        "rhr": 47
    }
    
    upsert_res = supabase.table("daily_summaries").upsert(test_row).execute()
    print("   Upsert successful! Row returned:")
    print("  ", upsert_res.data)

    # 5. Insert a habit log including any_caffeine
    print("\n5. Testing UPSERT on habit_logs (with any_caffeine)...")
    habit_row = {
        "user_id": user_id,
        "date": "2026-09-02",
        "alcohol": False,
        "late_meal": False,
        "late_caffeine": False,
        "any_caffeine": True,
        "screen_in_bed": False,
        "travel_day": False
    }
    habit_res = supabase.table("habit_logs").upsert(habit_row).execute()
    print("   Habit log upsert successful! Row returned:")
    print("  ", habit_res.data)

    print("\nAll RLS permissions and authenticated flows are verified!")

if __name__ == "__main__":
    run()
