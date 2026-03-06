import argparse
import ctypes
import os
import signal
import sys

from bitcraft_preview.config import DEBUG, ensure_config_exists, get_config_file_path
from bitcraft_preview.logging_setup import init_logging
from bitcraft_preview.native import (
    NativeProcessControlError,
    NativeProcessController,
    NativeSetupError,
    NativeSetupService,
    setup_disclaimer_text,
)


def get_asset_path(asset_name):
    """Get the path to an asset file, handling both dev and packaged modes."""
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
        return os.path.join(base_path, "assets", asset_name)

    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, "bitcraft_preview", "assets", asset_name)


def _run_native_cli(args) -> None:
    # Initialize logging for CLI operations to ensure debug info is captured.
    logger = init_logging()
    if ensure_config_exists():
        logger.info("Using config file: %s", get_config_file_path())
    
    try:
        if args.native_setup is not None:
            if not args.native_ack_user_changes:
                print(setup_disclaimer_text())
                print("\nSetup aborted. Re-run with --native-ack-user-changes to continue.")
                raise SystemExit(2)

            service = NativeSetupService()
            summary = service.reconcile(args.native_setup)
            print(
                "Native setup complete:",
                f"users_created={summary.users_created}",
                f"users_reused={summary.users_reused}",
                f"folders_created={summary.folders_created}",
                f"folders_reused={summary.folders_reused}",
                f"folders_repaired={summary.folders_repaired}",
            )
            return

        if args.native_cleanup:
            if not args.native_ack_user_changes:
                print(setup_disclaimer_text())
                print("\nCleanup aborted. Re-run with --native-ack-user-changes to continue.")
                raise SystemExit(2)

            service = NativeSetupService()
            summary = service.cleanup()
            print(
                "Native cleanup complete:",
                f"users_deleted={summary.users_deleted}",
                f"users_failed={summary.users_failed}",
                f"folders_deleted={summary.folders_deleted}",
                f"folders_failed={summary.folders_failed}",
            )
            return

        controller = NativeProcessController()
        if args.native_launch:
            result = controller.launch_instance(args.native_launch)
            logger.info("Launched %s (%s) steam_pid=%s", result.instance_id, result.local_username, result.steam_pid)
            print(f"Launched {result.instance_id} ({result.local_username}) steam_pid={result.steam_pid}")
        elif args.native_restart:
            result = controller.restart_instance(args.native_restart)
            logger.info("Restarted %s (%s) steam_pid=%s", result.instance_id, result.local_username, result.steam_pid)
            print(f"Restarted {result.instance_id} ({result.local_username}) steam_pid={result.steam_pid}")
        elif args.native_relogin:
            result = controller.relogin_instance(args.native_relogin)
            logger.info("Re-login launched %s (%s) steam_pid=%s", result.instance_id, result.local_username, result.steam_pid)
            print(f"Re-login launched {result.instance_id} ({result.local_username}) steam_pid={result.steam_pid}")
    except NativeSetupError as e:
        logger.error("Native setup error: %s", e)
        print(f"Native setup error: {e}")
        raise SystemExit(2)
    except NativeProcessControlError as e:
        logger.error("Native mode error: %s", e)
        print(f"Native mode error: {e}")
        raise SystemExit(2)
    except Exception as e:
        logger.exception("Native mode unexpected error")
        print(f"Native mode unexpected error: {e}")
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("--native-launch", dest="native_launch", help="Launch native instance by instance_id or local username")
    parser.add_argument("--native-restart", dest="native_restart", help="Restart native instance by instance_id or local username")
    parser.add_argument("--native-relogin", dest="native_relogin", help="Re-login native instance by instance_id or local username")
    parser.add_argument("--native-setup", dest="native_setup", type=int, help="Reconcile and provision native setup for N instances")
    parser.add_argument("--native-cleanup", dest="native_cleanup", action="store_true", help="Cleanup app-managed native users/folders")
    parser.add_argument(
        "--native-ack-user-changes",
        dest="native_ack_user_changes",
        action="store_true",
        help="Acknowledge Windows user account modifications for native setup/cleanup",
    )
    args = parser.parse_args()

    native_request = (
        args.native_launch
        or args.native_restart
        or args.native_relogin
        or args.native_setup is not None
        or args.native_cleanup
    )
    if native_request:
        _run_native_cli(args)
        return

    mutex_name = "Global\\BitCraftPreview_SingleInstanceMutex"
    kernel32 = ctypes.windll.kernel32
    _mutex = kernel32.CreateMutexW(None, False, mutex_name)
    last_error = kernel32.GetLastError()
    if last_error == 183:
        print("BitCraftPreview is already running. Exiting.")
        return

    from PySide6.QtGui import QAction, QIcon
    from PySide6.QtWidgets import QApplication, QInputDialog, QMenu, QMessageBox, QSystemTrayIcon

    from bitcraft_preview.ui.overlay_manager import OverlayManager

    logger = init_logging()
    logger.info("Starting BitCraft Preview application")
    if ensure_config_exists():
        logger.info("Using config file: %s", get_config_file_path())
    else:
        logger.error("Failed to create config file: %s", get_config_file_path())

    app = QApplication(sys.argv)

    if DEBUG:
        signal.signal(signal.SIGINT, signal.SIG_DFL)

    app.setQuitOnLastWindowClosed(False)

    tray_icon = QSystemTrayIcon()
    systemtray_icon_path = get_asset_path("systemtray.ico")
    if os.path.exists(systemtray_icon_path):
        tray_icon.setIcon(QIcon(systemtray_icon_path))
    else:
        logger.warning("System tray icon not found at: %s", systemtray_icon_path)
        fallback_icon = app.style().standardIcon(app.style().StandardPixmap.SP_ComputerIcon)
        tray_icon.setIcon(fallback_icon)
    tray_icon.setToolTip("BitCraft Preview")

    tray_menu = QMenu()

    def _confirm_native_account_changes(operation_name: str) -> bool:
        text = f"{setup_disclaimer_text()}\n\nProceed with {operation_name}?"
        choice = QMessageBox.warning(
            None,
            "Native Mode Account Changes",
            text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return choice == QMessageBox.StandardButton.Yes

    def _run_native_setup_from_tray() -> None:
        count, ok = QInputDialog.getInt(
            None,
            "Native Mode Setup",
            "How many native instances should be configured?",
            value=8,
            minValue=1,
            maxValue=32,
        )
        if not ok:
            return

        if not _confirm_native_account_changes(f"Native setup for {count} instance(s)"):
            return

        try:
            summary = NativeSetupService().reconcile(count)
            message = (
                "Native setup complete.\n"
                f"users_created={summary.users_created}, users_reused={summary.users_reused}\n"
                f"folders_created={summary.folders_created}, folders_reused={summary.folders_reused}, "
                f"folders_repaired={summary.folders_repaired}"
            )
            logger.info(message)
            QMessageBox.information(None, "Native Setup Complete", message)
        except NativeSetupError as e:
            logger.error("Native setup failed from tray: %s", e)
            QMessageBox.critical(None, "Native Setup Error", str(e))
        except Exception as e:
            logger.exception("Unexpected tray native setup error")
            QMessageBox.critical(None, "Native Setup Error", str(e))

    def _run_native_cleanup_from_tray() -> None:
        if not _confirm_native_account_changes("Native cleanup"):
            return

        confirm = QMessageBox.warning(
            None,
            "Confirm Native Cleanup",
            (
                "This will delete:\n"
                "- App-managed local Windows users (bitcraft1, bitcraft2, ...)\n"
                "- App-managed Steam instance folders under configured steam_instance_root\n\n"
                "Use this only when you want to fully revert Native Mode. Continue?"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            summary = NativeSetupService().cleanup()
            message = (
                "Native cleanup complete.\n"
                f"users_deleted={summary.users_deleted}, users_failed={summary.users_failed}\n"
                f"folders_deleted={summary.folders_deleted}, folders_failed={summary.folders_failed}"
            )
            logger.info(message)
            QMessageBox.information(None, "Native Cleanup Complete", message)
        except NativeSetupError as e:
            logger.error("Native cleanup failed from tray: %s", e)
            QMessageBox.critical(None, "Native Cleanup Error", str(e))
        except Exception as e:
            logger.exception("Unexpected tray native cleanup error")
            QMessageBox.critical(None, "Native Cleanup Error", str(e))

    native_setup_action = QAction("Native Setup...", app)
    native_setup_action.triggered.connect(_run_native_setup_from_tray)
    tray_menu.addAction(native_setup_action)

    native_cleanup_action = QAction("Native Cleanup...", app)
    native_cleanup_action.triggered.connect(_run_native_cleanup_from_tray)
    tray_menu.addAction(native_cleanup_action)

    tray_menu.addSeparator()

    quit_action = QAction("Quit", app)
    quit_action.triggered.connect(app.quit)
    tray_menu.addAction(quit_action)

    tray_icon.setContextMenu(tray_menu)
    tray_icon.show()

    _manager = OverlayManager()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
