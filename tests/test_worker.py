import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from src.worker import Worker


class WorkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.prompt = root / "worker.txt"
        self.revision_prompt = root / "revision.txt"
        self.prompt.write_text("Kaynak:{source_text}\nSoru:{question}", encoding="utf-8")
        self.revision_prompt.write_text(
            "{source_text}|{question}|{worker_answer}|{feedback}", encoding="utf-8"
        )
        self.worker = Worker(
            prompt_path=self.prompt,
            revision_prompt_path=self.revision_prompt,
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_build_prompt_contains_only_worker_inputs(self) -> None:
        prompt = self.worker._build_prompt("Metin", "Soru?")
        self.assertEqual(prompt, "Kaynak:Metin\nSoru:Soru?")
        self.assertNotIn("expected_answer", prompt)

    def test_empty_input_fails_before_model_call(self) -> None:
        with patch.object(self.worker, "_call_model") as call_model:
            with self.assertRaises(ValueError):
                self.worker.ask("", "Soru?")
        call_model.assert_not_called()

    def test_json_answer_field_is_normalized_to_plain_text(self) -> None:
        response = SimpleNamespace(
            message=SimpleNamespace(
                content='{"answer":"42 birim","explanation":"gizli"}'
            )
        )
        with patch("src.worker.chat", return_value=response):
            answer = self.worker._call_model("prompt")
        self.assertEqual(answer, "42 birim")

    def test_json_predicted_answer_field_is_normalized(self) -> None:
        response = SimpleNamespace(
            message=SimpleNamespace(
                content=(
                    '{"predicted_answer":"43 birim",'
                    '"reasoning":"gizli"}'
                )
            )
        )
        with patch("src.worker.chat", return_value=response):
            answer = self.worker._call_model("prompt")
        self.assertEqual(answer, "43 birim")

    def test_plain_text_answer_is_unchanged(self) -> None:
        response = SimpleNamespace(
            message=SimpleNamespace(content="44 birim")
        )
        with patch("src.worker.chat", return_value=response):
            answer = self.worker._call_model("prompt")
        self.assertEqual(answer, "44 birim")


if __name__ == "__main__":
    unittest.main()
