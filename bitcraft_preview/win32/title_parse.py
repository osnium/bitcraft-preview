import re
import psutil
import logging

logger = logging.getLogger("bitcraft_preview")

# `[#] [SandboxName] BitCraft [#]`
TITLE_PATTERN = re.compile(r"\[[#\d]+\]\s+\[(.*?)\]\s+BitCraft\s+\[?[#\d]*\]?")

def parse_sandbox_name(title: str) -> str | None:
    match = TITLE_PATTERN.search(title)
    if match:
        return match.group(1).strip()
    return None


def _get_process_username(pid: int) -> str | None:
    """Get the username that owns a process."""
    try:
        proc = psutil.Process(pid)
        return proc.username().split("\\")[-1].lower()  # Extract username from DOMAIN\username
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return None


def _get_native_instance_label(pid: int) -> str | None:
    """Get display label for native mode instances by matching process owner to config."""
    try:
        username = _get_process_username(pid)
        if not username:
            return None
        
        # Only check for native instances if username matches pattern (bitcraft1, bitcraft2, etc.)
        if not username.startswith("bitcraft"):
            return None
        
        # Lazy import to avoid circular dependencies
        from bitcraft_preview.config import load_config
        
        cfg = load_config()
        native_cfg = cfg.get("native_mode", {})
        
        if not native_cfg.get("enabled"):
            return None
        
        instances = native_cfg.get("instances", [])
        for instance in instances:
            if instance.get("local_username", "").lower() == username:
                # Prefer overlay_nickname, fall back to instance_id
                nickname = instance.get("overlay_nickname", "").strip()
                if nickname:
                    return nickname
                instance_id = instance.get("instance_id", "").strip()
                if instance_id:
                    return instance_id
                return username  # Ultimate fallback
        
        # If we have a bitcraftN user but no matching config, show username
        return username
    except Exception as e:
        logger.debug(f"Error getting native instance label for PID {pid}: {e}")
        return None


def display_label(title: str, pid: int | None = None) -> str:
    """
    Determine display label for a window.
    
    For Sandboxie: Extract sandbox name from title pattern.
    For Native Mode: Match process owner to native instance config.
    Fallback: Return raw title.
    """
    # Check for Sandboxie pattern first
    sandbox = parse_sandbox_name(title)
    if sandbox:
        return sandbox
    
    # Check for native mode instance if PID provided
    if pid is not None:
        native_label = _get_native_instance_label(pid)
        if native_label:
            return native_label
    
    # Fallback to raw title
    return title
