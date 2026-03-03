import os
import sys

def init_logging():
    # just create empty loggers and dirs for now
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    log_dir = os.path.join(local_app_data, "BitCraftPreview")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "bitcraft_preview.log")

    # In a real app we'd configure logging module here. 
    # For now simply simple prints or minimal logging config.
    import logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger("bitcraft_preview")
