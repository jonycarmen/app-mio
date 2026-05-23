import logging
from pathlib import Path

# Ensure logs directory exists at import time
Path("logs").mkdir(exist_ok=True)

security_logger = logging.getLogger("security")
security_logger.setLevel(logging.INFO)

_handler = logging.FileHandler("logs/security.log", encoding="utf-8")
_handler.setLevel(logging.INFO)
_handler.setFormatter(
    logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
)
security_logger.addHandler(_handler)
# Prevent propagation to root logger to avoid duplicate output
security_logger.propagate = False
