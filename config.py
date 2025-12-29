# config.py
import os
from dotenv import load_dotenv

# ============================================================
# ENV
# ============================================================

load_dotenv()

ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY")

if not ROBOFLOW_API_KEY:
    raise RuntimeError("ROBOFLOW_API_KEY is not set in environment variables")

# ============================================================
# MODEL
# ============================================================

MODEL_ID = "shotdetect3-x79bc/3"
CONF_THRESHOLD = 0.3

# ============================================================
# PATHS
# ============================================================

OUTPUT_DIR = "img/out"

# ============================================================
# ISSF TARGET CONFIG
# ============================================================

ISSF_RADII_MM = {
    10: 5.5,
    9: 10.5,
    8: 15.5,
    7: 20.5,
    6: 25.5,
    5: 30.5,
    4: 35.5,
    3: 40.5,
    2: 45.5,
    1: 50.5
}

BULLET_RADIUS_MM = 4.5  # НЕ ДІЛИМО

# ============================================================
# VISUAL TOGGLES
# ============================================================

SHOW_DISTANCE_LINES = True
SHOW_DISTANCE_TEXT = True
SHOW_RING_NUMBERS = True
SHOW_BULLET_OUTLINE = True
