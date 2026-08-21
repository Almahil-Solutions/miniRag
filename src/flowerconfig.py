import os
from dotenv import dotenv_values

_env_file_vals = dotenv_values(".env")

flower_user = os.getenv("CELERY_FLOWER_USER") or _env_file_vals.get("CELERY_FLOWER_USER", "admin")
flower_pass = os.getenv("CELERY_FLOWER_PASSWORD") or _env_file_vals.get("CELERY_FLOWER_PASSWORD", "")

# Flower Configuration
port = 5555
max_tasks = 10000
auto_refresh = True

# Authentication: Enforce Basic Auth whenever credentials are provided
if flower_pass:
    basic_auth = [f"{flower_user}:{flower_pass}"]
else:
    # Require authentication if running in production
    if os.getenv("APP_ENV", "production") == "production":
        raise RuntimeError("CELERY_FLOWER_PASSWORD must be configured in production.")