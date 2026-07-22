import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("gerar_rascunho.py")
SPEC = importlib.util.spec_from_file_location("gerar_rascunho", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class GerarRascunhoTest(unittest.TestCase):
    def test_extracts_json_from_fence(self):
        self.assertEqual(MODULE.extract_json('```json\n{"ok": true}\n```'), {"ok": True})

    def test_queue_skips_used_slug(self):
        queue = {"topics": [{"slug": "a"}, {"slug": "b"}]}
        self.assertEqual(MODULE.choose_topic(queue, {"a"})["slug"], "b")

    def test_dry_run_exposes_names_not_values(self):
        topic = {"slug": "a", "source_urls": ["https://example.com"]}
        status = MODULE.readiness("gemini", topic)
        self.assertFalse(status["will_publish"])
        self.assertIn("GEMINI_API_KEY", status["required_env"])


if __name__ == "__main__":
    unittest.main()
