import unittest

from bitcraft_preview.native.dpapi import protect_text, unprotect_text


class DpapiTests(unittest.TestCase):
    def test_roundtrip_machine_scope(self) -> None:
        secret = "native-mode-secret-123"
        encrypted = protect_text(secret, use_machine_scope=True)
        plain = unprotect_text(encrypted)
        self.assertEqual(plain, secret)


if __name__ == "__main__":
    unittest.main()
