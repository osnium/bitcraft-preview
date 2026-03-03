import re

# `[#] [SandboxName] BitCraft [#]`
TITLE_PATTERN = re.compile(r"\[[#\d]+\]\s+\[(.*?)\]\s+BitCraft\s+\[?[#\d]*\]?")

def parse_sandbox_name(title: str) -> str | None:
    match = TITLE_PATTERN.search(title)
    if match:
        return match.group(1).strip()
    return None

def display_label(title: str) -> str:
    sandbox = parse_sandbox_name(title)
    if sandbox:
        return sandbox
    return title
