# BitCraft Sandboxie Preview

A Windows-only utility to display **live DWM previews** of multiple BitCraft game clients running under Sandboxie Plus. It allows you to monitor all your running clients in a grid and quickly switch focus to a specific sandbox by simply clicking its preview tile.

This project is built directly for Windows using pure DWM API and PySide6 for minimal window overhead.

## Features

- **Live Previews**: Uses Windows Desktop Window Manager (`DWM`) thumbnails to show true, low-latency live feeds of all your BitCraft clients at once.
- **Auto-Discovery**: Automatically enumerates and identifies `BitCraft.exe` clients every second. 
- **Sandboxie Support**: Parses Sandboxie Plus injected Window Titles `[#] [SandboxName] BitCraft [#]` and labels your preview tiles correctly.
- **Quick Switching**: Restores minimized windows and reliably brings them to the foreground via a single mouse click. 

## Installation

### Prerequisites
- Python 3.11+
- Windows 10/11 (reliant on Windows DWM API)

### Local Development Setup

1. **Clone the repository**:
   ```powershell
   git clone https://github.com/your-repo/bitcraft-preview.git
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

## Usage

Simply launch the `bitcraft_preview` module from your activated virtual environment:

```powershell
python -m bitcraft_preview
```

As long as your BitCraft clients are running (vanilla or inside Sandboxie Plus), the tool will automatically detect them and add a corresponding live preview tile to the grid.

> **Testing Component**: You can quickly test if your system correctly supports DWM thumbnails by running `python ./scripts/sanity_check_thumbnail.py` and seeing if it spots and shows the game window.

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

## License

This project is open-source. See `LICENSE` file for details.
