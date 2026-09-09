import os
import math
from pathlib import Path
from zoneinfo import ZoneInfo

def load_env(env_path=None):
    """Loads environment variables from .env file without requiring external dependencies."""
    if env_path is None:
        # Search in current directory, parent directory, or root of project
        candidates = [
            Path(__file__).resolve().parent / ".env",
            Path(__file__).resolve().parent.parent / ".env",
            Path.cwd() / ".env"
        ]
        for c in candidates:
            if c.is_file():
                env_path = c
                break
    else:
        env_path = Path(env_path)

    if env_path and env_path.is_file():
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

# Normal CDF: use scipy if available, otherwise exact math.erf formulation
try:
    from scipy.stats import norm
    norm_cdf = norm.cdf
except ImportError:
    def norm_cdf(z: float) -> float:
        """Standard normal cumulative distribution function using math.erf."""
        return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
APP_USER_EMAIL = os.getenv("APP_USER_EMAIL")
APP_USER_PASSWORD = os.getenv("APP_USER_PASSWORD")
TOKENSTORE = os.path.expanduser("~/.garminconnect")
USER_TIMEZONE = ZoneInfo("Europe/Brussels")

def safe_round(val, decimals: int = 0, default=None):
    if val is None:
        return default
    try:
        f = float(val)
        return round(f, decimals) if decimals > 0 else int(round(f))
    except (ValueError, TypeError):
        return default
