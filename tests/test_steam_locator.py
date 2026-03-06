import os
import tempfile
import unittest

from bitcraft_preview.native.steam_locator import SteamLocatorError, find_bitcraft_install


class SteamLocatorTests(unittest.TestCase):
    def test_find_install_from_default_folder_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            steam_root = os.path.join(tmp, "Steam")
            exe_path = os.path.join(steam_root, "steamapps", "common", "BitCraft", "BitCraft.exe")
            os.makedirs(os.path.dirname(exe_path), exist_ok=True)
            with open(exe_path, "wb") as f:
                f.write(b"x")

            info = find_bitcraft_install(steam_root)
            self.assertEqual(info.library_path, steam_root)
            self.assertEqual(os.path.normpath(info.bitcraft_path), os.path.normpath(exe_path))

    def test_find_install_from_appmanifest_installdir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            steam_root = os.path.join(tmp, "Steam")
            library = os.path.join(tmp, "LibA")
            os.makedirs(os.path.join(steam_root, "steamapps"), exist_ok=True)
            os.makedirs(os.path.join(library, "steamapps", "common", "BitCraft Online"), exist_ok=True)

            with open(os.path.join(steam_root, "steamapps", "libraryfolders.vdf"), "w", encoding="utf-8") as f:
                f.write(
                    '"libraryfolders"\n{\n'
                    '    "0"\n    {\n'
                    f'        "path"\t\t"{library.replace("\\", "\\\\")}"\n'
                    '        "apps"\n        {\n'
                    '            "3454650"\t\t"1234567890"\n'
                    '        }\n'
                    '    }\n'
                    '}\n'
                )

            manifest_path = os.path.join(library, "steamapps", "appmanifest_3454650.acf")
            with open(manifest_path, "w", encoding="utf-8") as f:
                f.write(
                    '"AppState"\n{\n'
                    '    "appid"\t\t"3454650"\n'
                    '    "installdir"\t\t"BitCraft Online"\n'
                    '}\n'
                )

            exe_path = os.path.join(library, "steamapps", "common", "BitCraft Online", "BitCraft.exe")
            with open(exe_path, "wb") as f:
                f.write(b"x")

            info = find_bitcraft_install(steam_root)
            self.assertEqual(os.path.normpath(info.library_path), os.path.normpath(library))
            self.assertEqual(os.path.normpath(info.bitcraft_path), os.path.normpath(exe_path))

    def test_reports_clear_error_when_app_in_library_but_missing_exe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            steam_root = os.path.join(tmp, "Steam")
            library = os.path.join(tmp, "LibA")
            os.makedirs(os.path.join(steam_root, "steamapps"), exist_ok=True)
            os.makedirs(os.path.join(library, "steamapps"), exist_ok=True)

            with open(os.path.join(steam_root, "steamapps", "libraryfolders.vdf"), "w", encoding="utf-8") as f:
                f.write(
                    '"libraryfolders"\n{\n'
                    '    "0"\n    {\n'
                    f'        "path"\t\t"{library.replace("\\", "\\\\")}"\n'
                    '        "apps"\n        {\n'
                    '            "3454650"\t\t"1234567890"\n'
                    '        }\n'
                    '    }\n'
                    '}\n'
                )

            with self.assertRaises(SteamLocatorError) as ctx:
                find_bitcraft_install(steam_root)

            self.assertIn("could not be resolved", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
