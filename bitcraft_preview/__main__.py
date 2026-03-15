import argparse
import ctypes
import os
import signal
import sys

from bitcraft_preview.config import DEBUG, ensure_config_exists, get_config_file_path, get_gui_settings
from bitcraft_preview.logging_setup import init_logging
from bitcraft_preview.version import get_app_version
from bitcraft_preview.native import (
    NativeProcessControlError,
    NativeProcessController,
    NativeModeStateManager,
    NativeSetupError,
    NativeSetupService,
    is_admin,
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
    logger.info("Starting BitCraft Preview native CLI v%s", get_app_version())
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
        elif args.native_userchooser:
            result = controller.open_user_chooser(args.native_userchooser)
            logger.info(
                "Opened account chooser for %s (%s) steam_pid=%s",
                result.instance_id,
                result.local_username,
                result.steam_pid,
            )
            print(f"Opened account chooser for {result.instance_id} ({result.local_username}) steam_pid={result.steam_pid}")
        elif args.native_relogin:
            result = controller.relogin_instance(args.native_relogin)
            logger.info(
                "Opened account chooser for %s (%s) via legacy relogin flag steam_pid=%s",
                result.instance_id,
                result.local_username,
                result.steam_pid,
            )
            print(f"Opened account chooser for {result.instance_id} ({result.local_username}) steam_pid={result.steam_pid}")
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
    parser.add_argument(
        "--native-userchooser",
        dest="native_userchooser",
        help="Open Steam account chooser for a native instance by instance_id or local username",
    )
    parser.add_argument(
        "--native-relogin",
        dest="native_relogin",
        help="Legacy alias for --native-userchooser",
    )
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
        or args.native_userchooser
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

    from bitcraft_preview.ui.main_shell import MainShellWindow, build_dark_stylesheet
    from bitcraft_preview.ui.overlay_manager import OverlayManager

    logger = init_logging()
    logger.info("Starting BitCraft Preview application v%s", get_app_version())
    if ensure_config_exists():
        logger.info("Using config file: %s", get_config_file_path())
    else:
        logger.error("Failed to create config file: %s", get_config_file_path())

    app = QApplication(sys.argv)
    app.setStyleSheet(build_dark_stylesheet())

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
    native_accounts_menu = QMenu("Native Accounts", tray_menu)
    tools_menu = QMenu("Tools", tray_menu)
    _manager = None
    _shell = MainShellWindow()

    def _show_gui_shell() -> None:
        _shell.show_from_tray()

    def _show_settings_panel() -> None:
        _shell.show_panel("settings")
        _shell.show_from_tray()

    def _refresh_overlay_and_tray_labels() -> None:
        # Keep account labels and overlays in sync immediately after metadata edits.
        _rebuild_native_accounts_menu()
        if _manager is not None:
            _manager.refresh_windows()

    def _instance_menu_label(instance) -> str:
        controller = NativeProcessController()
        is_running = controller.is_instance_running(instance.instance_id)
        status_icon = "🟢" if is_running else "⚫"
        
        nickname = (instance.overlay_nickname or "").strip()
        if nickname:
            return f"{status_icon} {nickname}"
        return f"{status_icon} {instance.instance_id}"

    def _show_native_action_error(title: str, e: Exception) -> None:
        logger.error("%s: %s", title, e)
        QMessageBox.critical(None, title, str(e))

    def _update_instance_metadata(instance_id: str, *, entity_id: str | None = None, overlay_nickname: str | None = None) -> None:
        state = NativeModeStateManager()
        instance = state.get_instance(instance_id)
        if instance is None:
            raise NativeProcessControlError(f"Unknown native instance: {instance_id}")

        state.upsert_instance(
            instance_id=instance.instance_id,
            local_username=instance.local_username,
            entity_id=entity_id,
            overlay_nickname=overlay_nickname,
            status=instance.status,
        )

    def _set_entity_id_from_tray(instance_id: str) -> None:
        state = NativeModeStateManager()
        instance = state.get_instance(instance_id)
        if instance is None:
            QMessageBox.critical(None, "Native Account Error", f"Unknown native instance: {instance_id}")
            return

        value, ok = QInputDialog.getText(
            None,
            "Set Entity ID",
            f"Enter Entity ID for {instance.instance_id} ({instance.local_username})\nLeave blank to clear:",
            text=instance.entity_id,
        )
        if not ok:
            return

        try:
            _update_instance_metadata(instance.instance_id, entity_id=value.strip(), overlay_nickname=None)
            logger.info("Updated entity_id for %s", instance.instance_id)
            _refresh_overlay_and_tray_labels()
        except Exception as e:
            _show_native_action_error("Set Entity ID Error", e)

    def _set_overlay_name_from_tray(instance_id: str) -> None:
        state = NativeModeStateManager()
        instance = state.get_instance(instance_id)
        if instance is None:
            QMessageBox.critical(None, "Native Account Error", f"Unknown native instance: {instance_id}")
            return

        value, ok = QInputDialog.getText(
            None,
            "Set Overlay Name",
            f"Enter Overlay Name for {instance.instance_id} ({instance.local_username})\nLeave blank to clear:",
            text=instance.overlay_nickname,
        )
        if not ok:
            return

        try:
            _update_instance_metadata(instance.instance_id, entity_id=None, overlay_nickname=value.strip())
            logger.info("Updated overlay_nickname for %s", instance.instance_id)
            _refresh_overlay_and_tray_labels()
        except Exception as e:
            _show_native_action_error("Set Overlay Name Error", e)

    def _launch_or_restart_from_tray(instance_id: str) -> None:
        try:
            result, was_restart = NativeProcessController().launch_or_restart(instance_id)
            verb = "Restarted" if was_restart else "Launched"
            logger.info("%s %s (%s) steam_pid=%s", verb, result.instance_id, result.local_username, result.steam_pid)
            if DEBUG:
                QMessageBox.information(
                    None,
                    f"Native {verb}",
                    f"{verb} {result.instance_id} ({result.local_username}) steam_pid={result.steam_pid}",
                )
        except NativeProcessControlError as e:
            _show_native_action_error("Native Launch/Restart Error", e)
        except Exception as e:
            logger.exception("Unexpected tray launch/restart error")
            _show_native_action_error("Native Launch/Restart Error", e)

    def _open_user_chooser_from_tray(instance_id: str) -> None:
        try:
            result = NativeProcessController().open_user_chooser(instance_id)
            message = f"Opened account chooser for {result.instance_id} ({result.local_username}) steam_pid={result.steam_pid}"
            logger.info(message)
            if DEBUG:
                QMessageBox.information(None, "Native Account Chooser", message)
        except NativeProcessControlError as e:
            _show_native_action_error("Native Account Chooser Error", e)
        except Exception as e:
            logger.exception("Unexpected tray native account chooser error")
            _show_native_action_error("Native Account Chooser Error", e)

    def _kill_instance_from_tray(instance_id: str) -> None:
        try:
            controller = NativeProcessController()
            controller.force_kill_instance_processes(instance_id, timeout=10.0)
            message = f"Force-killed processes for {instance_id}"
            logger.info(message)
            if DEBUG:
                QMessageBox.information(None, "Native Kill", message)
        except NativeProcessControlError as e:
            _show_native_action_error("Native Kill Error", e)
        except Exception as e:
            logger.exception("Unexpected tray native kill error")
            _show_native_action_error("Native Kill Error", e)

    def _launch_all_instances_from_tray() -> None:
        state = NativeModeStateManager()
        instances = state.list_instances()
        if not instances:
            QMessageBox.information(None, "Native Launch All", "No native accounts configured.")
            return

        controller = NativeProcessController()
        launched = []
        skipped = []
        failed = []

        for instance in instances:
            try:
                if controller.is_instance_running(instance.instance_id):
                    skipped.append(instance.instance_id)
                    continue
                result = controller.launch_instance(instance.instance_id)
                launched.append(f"{result.instance_id} ({result.local_username})")
            except Exception as e:
                logger.error("Launch-all failed for %s: %s", instance.instance_id, e)
                failed.append(f"{instance.instance_id}: {e}")

        logger.info("Launch all complete: launched=%s skipped=%s failed=%s", len(launched), len(skipped), len(failed))
        if failed:
            details = "\n".join(failed)
            QMessageBox.critical(None, "Native Launch All Error", f"Some accounts failed to launch:\n{details}")
            return

        if DEBUG:
            QMessageBox.information(
                None,
                "Native Launch All",
                f"launched={len(launched)}, already_running={len(skipped)}",
            )

    def _kill_all_instances_from_tray() -> None:
        state = NativeModeStateManager()
        instances = state.list_instances()
        if not instances:
            QMessageBox.information(None, "Kill All Instances", "No native accounts configured.")
            return

        # Build instance list with status and avoid redundant instance_id/username display
        instance_lines = []
        for inst in instances:
            label = _instance_menu_label(inst)  # includes status icon and nickname/instance_id
            nickname = (inst.overlay_nickname or "").strip()
            # Only add username in parens if nickname is set (to show which Windows account)
            if nickname:
                instance_lines.append(f"• {label} ({inst.local_username})")
            else:
                # instance_id already in label, username would be redundant
                instance_lines.append(f"• {label}")
        
        instance_list = "\n".join(instance_lines)
        confirm = QMessageBox.warning(
            None,
            "Confirm Kill All",
            f"Force-kill all Steam and BitCraft processes for all native instances?\n\nThis will immediately terminate:\n{instance_list}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            controller = NativeProcessController()
            count = controller.kill_all_instances(timeout=10.0)
            message = f"Killed {count} process(es) across all native instances."
            logger.info(message)
            if DEBUG:
                QMessageBox.information(None, "Kill All Complete", message)
        except Exception as e:
            logger.exception("Kill all failed: %s", e)
            QMessageBox.critical(None, "Kill All Error", str(e))

    def _rebuild_native_accounts_menu() -> None:
        native_accounts_menu.clear()
        instances = NativeModeStateManager().list_instances()
        if not instances:
            empty_action = QAction("No Native Accounts Configured", app)
            empty_action.setEnabled(False)
            native_accounts_menu.addAction(empty_action)
            return

        launch_all_action = QAction("Launch All (Not Running)", app)
        launch_all_action.triggered.connect(_launch_all_instances_from_tray)
        native_accounts_menu.addAction(launch_all_action)
        
        kill_all_action = QAction("Kill All Instances", app)
        kill_all_action.triggered.connect(_kill_all_instances_from_tray)
        native_accounts_menu.addAction(kill_all_action)
        
        native_accounts_menu.addSeparator()

        controller = NativeProcessController()
        for instance in instances:
            account_menu = QMenu(_instance_menu_label(instance), native_accounts_menu)

            is_running = controller.is_instance_running(instance.instance_id)
            launch_restart_action = QAction("Restart" if is_running else "Launch", app)
            launch_restart_action.triggered.connect(
                lambda _checked=False, instance_id=instance.instance_id: _launch_or_restart_from_tray(instance_id)
            )
            account_menu.addAction(launch_restart_action)

            chooser_action = QAction("Open Account Chooser", app)
            chooser_action.triggered.connect(
                lambda _checked=False, instance_id=instance.instance_id: _open_user_chooser_from_tray(instance_id)
            )
            account_menu.addAction(chooser_action)

            kill_action = QAction("Kill", app)
            kill_action.triggered.connect(lambda _checked=False, instance_id=instance.instance_id: _kill_instance_from_tray(instance_id))
            account_menu.addAction(kill_action)

            account_menu.addSeparator()

            set_entity_id_action = QAction("Set Entity ID...", app)
            set_entity_id_action.triggered.connect(lambda _checked=False, instance_id=instance.instance_id: _set_entity_id_from_tray(instance_id))
            account_menu.addAction(set_entity_id_action)

            set_overlay_name_action = QAction("Set Overlay Name...", app)
            set_overlay_name_action.triggered.connect(lambda _checked=False, instance_id=instance.instance_id: _set_overlay_name_from_tray(instance_id))
            account_menu.addAction(set_overlay_name_action)

            native_accounts_menu.addMenu(account_menu)

    def _open_file_path(path: str, title: str) -> None:
        try:
            if not os.path.exists(path):
                QMessageBox.warning(None, title, f"Path does not exist:\n{path}")
                return
            os.startfile(path)
        except Exception as e:
            _show_native_action_error(title, e)

    def _open_config_from_tray() -> None:
        _open_file_path(get_config_file_path(), "Open Config Error")

    def _open_log_from_tray() -> None:
        log_path = os.path.join(os.environ.get("LOCALAPPDATA", ""), "BitCraftPreview", "bitcraft_preview.log")
        _open_file_path(log_path, "Open Log Error")

    def _require_native_admin(operation_name: str) -> bool:
        if is_admin():
            return True

        message = (
            f"Native Mode {operation_name} requires Administrator privileges. "
            "Please run BitCraftPreview.exe as Administrator."
        )
        logger.warning("Blocked native %s because process is not elevated", operation_name)
        QMessageBox.warning(None, "Administrator Privileges Required", message)
        return False

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
        if not _require_native_admin("setup"):
            return

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
            _refresh_overlay_and_tray_labels()
        except NativeSetupError as e:
            logger.error("Native setup failed from tray: %s", e)
            QMessageBox.critical(None, "Native Setup Error", str(e))
        except Exception as e:
            logger.exception("Unexpected tray native setup error")
            QMessageBox.critical(None, "Native Setup Error", str(e))

    def _run_native_cleanup_from_tray() -> None:
        if not _require_native_admin("cleanup"):
            return

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
            _refresh_overlay_and_tray_labels()
        except NativeSetupError as e:
            logger.error("Native cleanup failed from tray: %s", e)
            QMessageBox.critical(None, "Native Cleanup Error", str(e))
        except Exception as e:
            logger.exception("Unexpected tray native cleanup error")
            QMessageBox.critical(None, "Native Cleanup Error", str(e))

    open_gui_action = QAction("Open GUI", app)
    open_gui_action.triggered.connect(_show_gui_shell)
    tray_menu.addAction(open_gui_action)

    open_settings_action = QAction("Open Settings", app)
    open_settings_action.triggered.connect(_show_settings_panel)
    tray_menu.addAction(open_settings_action)

    tray_menu.addSeparator()

    _rebuild_native_accounts_menu()
    native_accounts_menu.aboutToShow.connect(_rebuild_native_accounts_menu)
    tray_menu.addMenu(native_accounts_menu)

    native_setup_action = QAction("Native Setup...", app)
    native_setup_action.triggered.connect(_run_native_setup_from_tray)
    tools_menu.addAction(native_setup_action)

    native_cleanup_action = QAction("Native Cleanup...", app)
    native_cleanup_action.triggered.connect(_run_native_cleanup_from_tray)
    tools_menu.addAction(native_cleanup_action)

    tools_menu.addSeparator()

    open_config_action = QAction("Open Config", app)
    open_config_action.triggered.connect(_open_config_from_tray)
    tools_menu.addAction(open_config_action)

    open_log_action = QAction("Open Log", app)
    open_log_action.triggered.connect(_open_log_from_tray)
    tools_menu.addAction(open_log_action)

    tray_menu.addMenu(tools_menu)

    tray_menu.addSeparator()

    quit_action = QAction("Quit", app)
    quit_action.triggered.connect(app.quit)
    tray_menu.addAction(quit_action)

    tray_icon.setContextMenu(tray_menu)
    tray_icon.activated.connect(lambda reason: _show_gui_shell() if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None)
    tray_icon.show()

    _manager = OverlayManager()

    if get_gui_settings().get("open_on_startup", False):
        _show_gui_shell()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
