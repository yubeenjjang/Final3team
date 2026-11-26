"""Check the W28 model request without calling OpenAI or storing a key."""

import io
import json
import unittest

from agents.reflection_model import generate_reflection


class ReflectionModelTests(unittest.TestCase):
    def test_structured_request_and_usage(self):
        seen = {}
        class Response(io.BytesIO):
            def __enter__(self):
                return self
            def __exit__(self, *_):
                self.close()
        def fake_urlopen(req, timeout):
            seen["payload"] = json.loads(req.data)
            seen["timeout"] = timeout
            return Response(json.dumps({"status": "completed", "model": "test-model",
                "usage": {"input_tokens": 40, "output_tokens": 12},
                "output": [{"type": "message", "content": [{"type": "output_text", "text":
                    json.dumps({"decision": "recheck", "reason": "id_mismatch",
                                "explanation": "요청한 F01과 반환 F02가 다릅니다."})}]}]}).encode())
        result = generate_reflection({"festival_id": "F01", "first_issue": "id_mismatch"},
                                     api_key="test-key", model="test-model", urlopen=fake_urlopen)
        self.assertEqual(result["decision"], "recheck")
        self.assertEqual(result["usage"]["input_tokens"], 40)
        self.assertFalse(seen["payload"]["store"])
        self.assertTrue(seen["payload"]["text"]["format"]["strict"])
        self.assertEqual(seen["timeout"], 20)
        self.assertNotIn("first_issue", seen["payload"]["input"][1]["content"])
        self.assertIn("F01", seen["payload"]["input"][1]["content"])

    def test_invalid_reason_is_rejected(self):
        class Response(io.BytesIO):
            def __enter__(self):
                return self
            def __exit__(self, *_):
                self.close()
        def fake_urlopen(*_args, **_kwargs):
            return Response(json.dumps({"status": "completed", "output": [{"type": "message",
                "content": [{"type": "output_text", "text": json.dumps({
                    "decision": "recheck", "reason": "other", "explanation": "x"})}]}]}).encode())
        with self.assertRaises(ValueError):
            generate_reflection({"festival_id": "F01"}, api_key="test-key", urlopen=fake_urlopen)


if __name__ == "__main__":
    unittest.main()
