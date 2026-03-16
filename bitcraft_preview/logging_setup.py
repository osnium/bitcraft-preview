import os
import sys
import logging
from datetime import datetime
from pathlib import Path

from bitcraft_preview.config import DEBUG, LOG_DIR_NAME, LOG_FILE_NAME

_KEEP_SESSION_LOGS = 5
_SESSION_LOG_PATH: Path | None = None
_LOGGING_CONFIGURED = False


def _resolve_log_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        return Path(local_app_data) / LOG_DIR_NAME

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent

    return Path(__file__).resolve().parent.parent


def _session_log_filename() -> str:
    stem, ext = os.path.splitext(LOG_FILE_NAME)
    if not ext:
        ext = ".log"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{stem}_{timestamp}{ext}"


def _iter_session_logs(log_dir: Path):
    stem, ext = os.path.splitext(LOG_FILE_NAME)
    if not ext:
        ext = ".log"
    pattern = f"{stem}_*{ext}"
    return [path for path in log_dir.glob(pattern) if path.is_file()]


def _prune_old_session_logs(log_dir: Path, keep: int = _KEEP_SESSION_LOGS) -> None:
    session_logs = sorted(_iter_session_logs(log_dir), key=lambda p: p.stat().st_mtime, reverse=True)
    for stale_log in session_logs[keep:]:
        try:
            stale_log.unlink()
        except OSError:
            # Best-effort cleanup only.
            pass


def get_latest_log_file_path() -> str | None:
    if _SESSION_LOG_PATH and _SESSION_LOG_PATH.exists():
        return str(_SESSION_LOG_PATH)

    log_dir = _resolve_log_dir()
    if not log_dir.exists():
        return None

    session_logs = sorted(_iter_session_logs(log_dir), key=lambda p: p.stat().st_mtime, reverse=True)
    if not session_logs:
        return None
    return str(session_logs[0])

def init_logging():
    global _SESSION_LOG_PATH, _LOGGING_CONFIGURED

    if _LOGGING_CONFIGURED:
        return logging.getLogger("bitcraft_preview")

    log_dir = _resolve_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    _SESSION_LOG_PATH = log_dir / _session_log_filename()

    logging.basicConfig(
        level=logging.DEBUG if DEBUG else logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(_SESSION_LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ],
        force=True,
    )
    _LOGGING_CONFIGURED = True

    _prune_old_session_logs(log_dir, keep=_KEEP_SESSION_LOGS)

    logger = logging.getLogger("bitcraft_preview")
    logger.info("Session log file: %s", _SESSION_LOG_PATH)
    return logger
