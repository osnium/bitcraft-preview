import os
import sys
import logging
import re
from datetime import datetime
from pathlib import Path

from bitcraft_preview.config import DEBUG, LOG_DIR_NAME, LOG_FILE_NAME

_KEEP_SESSION_LOGS = 5
_LATEST_LOG_NAME = "latest.log"
_LOGS_SUBDIR = "logs"
_LOGGING_CONFIGURED = False


def _resolve_log_dir() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        return Path(local_app_data) / LOG_DIR_NAME / _LOGS_SUBDIR

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / _LOGS_SUBDIR

    return Path(__file__).resolve().parent.parent / _LOGS_SUBDIR


def get_log_directory_path() -> str:
    return str(_resolve_log_dir())


def _extract_log_timestamp(log_path: Path) -> datetime:
    try:
        with log_path.open("r", encoding="utf-8", errors="ignore") as f:
            first_line = f.readline().strip()
    except OSError:
        first_line = ""

    match = re.match(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", first_line)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            pass

    return datetime.fromtimestamp(log_path.stat().st_mtime)


def _rollover_latest_log(log_dir: Path) -> Path | None:
    latest_log = log_dir / _LATEST_LOG_NAME
    if not latest_log.exists():
        return None

    if latest_log.stat().st_size <= 0:
        try:
            latest_log.unlink()
        except OSError:
            pass
        return None

    stamp = _extract_log_timestamp(latest_log)
    stem, ext = os.path.splitext(LOG_FILE_NAME)
    if not ext:
        ext = ".log"

    archive_name = f"{stem}_{stamp.strftime('%Y%m%d_%H%M%S')}{ext}"
    archive_path = log_dir / archive_name
    suffix = 1
    while archive_path.exists():
        archive_path = log_dir / f"{stem}_{stamp.strftime('%Y%m%d_%H%M%S')}_{suffix}{ext}"
        suffix += 1

    try:
        latest_log.rename(archive_path)
    except OSError:
        return None

    return archive_path


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
    log_dir = _resolve_log_dir()
    if not log_dir.exists():
        return None

    latest_log = log_dir / _LATEST_LOG_NAME
    if latest_log.exists():
        return str(latest_log)

    session_logs = sorted(_iter_session_logs(log_dir), key=lambda p: p.stat().st_mtime, reverse=True)
    if not session_logs:
        return None
    return str(session_logs[0])

def init_logging():
    global _LOGGING_CONFIGURED

    if _LOGGING_CONFIGURED:
        return logging.getLogger("bitcraft_preview")

    log_dir = _resolve_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    archived_log = _rollover_latest_log(log_dir)
    latest_log_path = log_dir / _LATEST_LOG_NAME

    logging.basicConfig(
        level=logging.DEBUG if DEBUG else logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(latest_log_path, mode="w", encoding="utf-8"),
            logging.StreamHandler(sys.stdout)
        ],
        force=True,
    )
    _LOGGING_CONFIGURED = True

    _prune_old_session_logs(log_dir, keep=_KEEP_SESSION_LOGS)

    logger = logging.getLogger("bitcraft_preview")
    if archived_log is not None:
        logger.info("Archived previous session log to: %s", archived_log)
    logger.info("Latest log file: %s", latest_log_path)
    return logger
