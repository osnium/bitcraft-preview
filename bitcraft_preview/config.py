# Window classes to filter, process name, etc.
PROCESS_NAME = "BitCraft.exe"
REFRESH_INTERVAL_MS = 1000

LOG_DIR_NAME = "BitCraftPreview"
LOG_FILE_NAME = "bitcraft_preview.log"

# Set to True to display the sandbox name horizontally inside the thumbnail, 
# or False to keep the extra box beneath the thumbnail.
INLINE_LABEL = True

# Opacity level for the thumbnails and labels (range: 0.0 to 1.0)
PREVIEW_OPACITY = 0.8

# Set to True to allow closing the app via CTRL+C in the console
DEBUG = False

# Enable zooming the preview when hovering
HOVER_ZOOM_ENABLED = True

# Zoom level in percentage (e.g., 200 means 2x size). Min: 100, Max: 1000
HOVER_ZOOM_PERCENT = 200

# Clamp zoom percentage to prevent extreme values from crashing the app
HOVER_ZOOM_PERCENT = max(100, min(500, HOVER_ZOOM_PERCENT))

# Hide the overlay corresponding to the currently active/focused game client
HIDE_ACTIVE_WINDOW_OVERLAY = False
