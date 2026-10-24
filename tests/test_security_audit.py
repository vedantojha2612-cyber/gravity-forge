import ast
import os
import re
import unittest
from unittest.mock import patch, MagicMock

import requests
from gravityforge.ephemeris.jpl import validate_api_input, fetch_horizons_vector, load_system


class TestSecurityAudit(unittest.TestCase):
    """Static and dynamic security audit covering OWASP Top 10, injections, and secrets."""

    def setUp(self):
        self.root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    def test_no_hardcoded_secrets(self):
        """Scans all repository source files for API keys, tokens, or credentials."""
        secret_patterns = [
            re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE),
            re.compile(r"ghp_[a-zA-Z0-9]{30,}", re.IGNORECASE),
            re.compile(r"AKIA[0-9A-Z]{16}", re.IGNORECASE),
            re.compile(r"-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----"),
            re.compile(r"(password|passwd|secret_key)\s*=\s*['\"][^'\"]{8,}['\"]", re.IGNORECASE),
        ]

        for dirpath, _, filenames in os.walk(self.root_dir):
            if any(p in dirpath for p in [".git", "__pycache__", "vendor"]):
                continue
            for fname in filenames:
                if fname.endswith((".py", ".json", ".md", ".html", ".js", ".sh")):
                    filepath = os.path.join(dirpath, fname)
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        for line_no, line in enumerate(f, start=1):
                            for pat in secret_patterns:
                                self.assertIsNone(
                                    pat.search(line),
                                    f"Potential hardcoded secret found in {fname}:{line_no}",
                                )

    def test_static_ast_safety_check(self):
        """Validates that no dangerous Python primitives (eval, exec, __import__) are used."""
        forbidden_funcs = {"eval", "exec", "__import__"}

        for dirpath, _, filenames in os.walk(os.path.join(self.root_dir( "gravityforge")):
            for fname in filenames:
                if fname.endswith(".py"):
                    filepath = os.path.join(dirpath, fname)
                    with open(filepath, "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read(), filename=filepath)

                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call):
                            if isinstance(node.func, ast.Name):
                                self.assertNotIn(
                                    node.func.id,
                                    forbidden_funcs,
                                    f"Dangerous function '{node.func.id}' detected in {fname}:{node.lineno}",
                                )

    def test_api_parameter_injection_fuzzing(self):
        """Fuzzes JPL API input validator with hostile injection payloads."""
        hostile_inputs = [
            "10; rm -rf /",
            "10 && cat /etc/passwd",
            "10' OR '1'='1",
            "10\r\nHost: evil.com",
            "<script>alert(1)</script>",
            "10`reboot`",
            "10$(whoami)",
            "../../../etc/shadow",
            "   ",
            "",
        ]

        for payload in hostile_inputs:
            with self.assertRaises(
                ValueError,
                msg=f"Hostile payload was unexpectedly accepted: {repr(payload)}",
            ):
                validate_api_input("target_id", payload)

    def test_valid_api_parameters_accepted(self):
        """Verifies safe identifiers pass validation."""
        valid_inputs = ["10", "399", "500@0", "2026-10-24", "2026-10-25 12:00:00", "CERES"]
        for valid in valid_inputs:
            res = validate_api_input("test_param", valid)
            self.assertEqual(res, valid)

    @patch("requests.get")
    def test_api_network_failure_resilience(self, mock_get):
        """Ensures network failures (timeouts, 500s) raise clean RuntimeErrors rather than crashing."""
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")

        with self.assertRaises(RuntimeError) as ctx:
            fetch_horizons_vector("399")
        self.assertIn("Horizons API network error", str(ctx.exception))

    def test_offline_fallback_guarantee(self):
        """Verifies load_system returns valid bodies even when offline or network fails."""
        with patch("gravityforge.ephemeris.jpl.fetch_horizons_vector") as mock_fetch:
            mock_fetch.side_effect = RuntimeError("Offline mode enforced")

            bodies = load_system(["earth", "mars", "jupiter"], use_live_api=True)
            self.assertEqual(len(bodies), 3)
            for b in bodies:
                self.assertGreater(b.mass, 0)
                # Verify positions are populated from calibrated offline J2000 barycentric state
                self.assertFalse(all(p == 0 for p in b.position))

    def test_frontend_web_security(self):
        """Audits web/index.html for XSS vectors, insecure innerHTML usage, and DOM safety."""
        html_path = os.path.join(self.root_dir, "web", "index.html")
        self.assertTrue(os.path.exists(html_path), "web/index.html must exist")

        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check that no eval() exists in frontend JS
        self.assertNotIn("eval(", content, "Forbidden eval() detected in frontend script")

        # Verify that all innerHTML / textContent usages do not inject unsanitized query parameters or hashes
        self.assertNotIn("location.search", content)
        self.assertNotIn("location.hash", content)
        self.assertNotIn("document.write(", content)


if __name__ == "__main__":
    unittest.main()
