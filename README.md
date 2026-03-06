# BitCraft Sandboxie Preview

<img src="preview.gif" alt="Preview" width="50%" loop="infinite" />

A Windows-only utility to display **live DWM previews** of multiple BitCraft game clients running under Sandboxie Plus. It allows you to monitor all your running clients in a grid and quickly switch focus to a specific sandbox by simply clicking its preview tile.

This project is built directly for Windows using pure DWM API and PySide6 for minimal window overhead.

## Features

- **Live Previews**: Uses Windows Desktop Window Manager (`DWM`) thumbnails to show true, low-latency live feeds of all your BitCraft clients at once.
- **Auto-Discovery**: Automatically enumerates and identifies `BitCraft.exe` clients.. 
- **Sandboxie Support**: Parses Sandboxie Plus injected Window Titles `[#] [SandboxName] BitCraft [#]` and labels your preview tiles correctly.
- **Quick Switching**: Restores minimized windows and reliably brings them to the foreground via a single mouse click. 
- **Hover Zoom**: Hovering over a tile temporarily enlarges it.
- **Hidden When Active**: Automatically hides the overlay for the game client you are currently focused on (Toggleable). 

## Configuration

When the application runs for the first time, it will automatically generate a `config.json` file in the same directory as the executable. You can open this file in Notepad or any text editor to change user settings:

```json
{
    "UserSettings": {
        "inline_label": true,                 // Needs Restart
        "preview_opacity": 0.8,               // Live Update
        "hover_zoom_enabled": true,           // Live Update
        "hover_zoom_percent": 200,            // Live Update (100-500)
            "hide_active_window_overlay": false,  // Live Update
            "switch_window_hotkey": "MOUSE5"     // Live Update (examples: MOUSE5, F8, CTRL+ALT+TAB)
    },
    ...
```
Settings marked as `Live Update` will apply immediately as soon as you save the file! Settings marked as `Needs Restart` will require you to quit the app from the System Tray and restart it.

## Installation

The easiest way to use BitCraft Sandboxie Preview is to download the pre-compiled executable.

1. Go to the [Releases](../../releases) page for this repository.
2. Download the latest `BitCraftPreview.zip` or `.exe` provided.
3. Extract the contents and run `BitCraftPreview.exe`.

## Usage

Simply launch the `BitCraftPreview.exe` file. 

The application is entirely borderless and invisible when there are no game clients running. 
As long as your BitCraft clients are running (vanilla or inside Sandboxie Plus), the tool will automatically detect them and add a corresponding live preview tile to your screen.

**To exit the application, right-click the BitCraftPreview icon in your Windows System Tray and click "Quit".**

### Local Development Setup

If you wish to compile or modify the application yourself:

1. **Clone the repository**:
   ```powershell
   git clone https://github.com/osnium/bitcraft-preview.git
   cd bitcraft-preview
   ```

2. **Create a virtual environment**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

3. **Install the package (editable mode)**:
   ```powershell
   pip install -e .
   ```

## Troubleshooting

- **No windows found**: Double check that your BitCraft executable is actually named `BitCraft.exe`. The application specifically filters for it in the Window Process identifiers.
- **Black / Blank thumbnails**: Some external graphical overlays or specific full-screen-exclusive contexts may interfere with DWM. Try verifying your game is in "Borderless / Windowed" instead of "Exclusive Fullscreen".
- **Focus Issues / Clicking doesn't work**: In rare environments, Windows prevents focus stealing. The app attempts `ShowWindowAsync` and `SetForegroundWindow`. If it fails, usually just clicking the target app on taskbar once manually and returning resolves the permission cycle.
- **Where are the logs in case something breaks?**: Application events and discovery operations are actively written to `%LOCALAPPDATA%\BitCraftPreview\bitcraft_preview.log`. 

## Packaging into a Standalone `.exe`

We use **PyInstaller** to package the script.

To generate a standalone executable bundle locally:
```powershell
pip install pyinstaller
pyinstaller --noconsole --onedir -n BitCraftPreview bitcraft_preview\__main__.py
```

The resulting files will be generated in `dist/BitCraftPreview/`. You can copy the entire folder anywhere and distribute it. 

## Support

If you wan't to support this project, make sure to check out Bitbucht in R18 / Oryxen and have it prosper :)

## License

This project is open-source. See `LICENSE` file for details.
