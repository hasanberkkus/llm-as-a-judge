import tempfile
import unittest
import inspect
from pathlib import Path
from unittest.mock import patch

from src.judge import Judge


class JudgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        prompt_path = root / "judge.txt"
        prompt_path.write_text(
            "{source_text}|{question}|{worker_answer}", encoding="utf-8"
        )
        self.judge = Judge(prompt_path=prompt_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    @staticmethod
    def valid_result() -> dict[str, object]:
        return {
            "reason": "Cevap doğrudur.",
            "correct_answer": "42 birim",
            "verdict": "Correct",
            "score": 10,
            "feedback": "Düzeltme gerekmiyor.",
        }

    def test_prompt_has_no_expected_answer(self) -> None:
        prompt = self.judge._build_prompt("Kaynak", "Soru", "Worker")
        self.assertEqual(prompt, "Kaynak|Soru|Worker")
        self.assertNotIn("expected", prompt.lower())

    def test_evaluate_uses_single_model_call(self) -> None:
        model_result = {
            "correct_answer": "Doğru",
            "verdict": "Incorrect",
            "score": 1,
            "reason": "Sonuç farklıdır.",
            "feedback": "Sonucu yeniden kontrol et.",
        }
        with patch.object(
            self.judge,
            "_call_model",
            return_value=model_result,
        ) as call_model:
            result = self.judge.evaluate("Kaynak", "Soru", "WORKER_SECRET")

        call_model.assert_called_once()
        prompt = call_model.call_args.args[0]
        self.assertIn("Kaynak", prompt)
        self.assertIn("Soru", prompt)
        self.assertIn("WORKER_SECRET", prompt)
        self.assertNotIn("expected_answer", prompt.lower())
        self.assertEqual(result["correct_answer"], "Doğru")

    def test_evaluate_all_does_not_carry_expected_answer(self) -> None:
        worker_answers = [
            {
                "question_id": 1,
                "question_type": "calculation",
                "question": "Soru",
                "predicted_answer": "42 birim",
                "expected_answer": "Judge bunu taşımamalı",
            }
        ]
        with patch.object(self.judge, "evaluate", return_value=self.valid_result()):
            result = self.judge.evaluate_all("Kaynak", worker_answers)[0]

        self.assertNotIn("expected_answer", result)
        self.assertEqual(
            set(result),
            {
                "question_id",
                "question_type",
                "question",
                "correct_answer",
                "worker_answer",
                "verdict",
                "score",
                "reason",
                "feedback",
            },
        )

    def test_missing_field_fails(self) -> None:
        result = self.valid_result()
        del result["reason"]
        with self.assertRaisesRegex(ValueError, "eksik"):
            Judge._validate_result(result)

    def test_invalid_verdict_fails(self) -> None:
        result = self.valid_result()
        result["verdict"] = "Maybe"
        with self.assertRaisesRegex(ValueError, "verdict"):
            Judge._validate_result(result)

    def test_score_must_be_integer(self) -> None:
        result = self.valid_result()
        result["score"] = 10.0
        with self.assertRaisesRegex(ValueError, "tam sayı"):
            Judge._validate_result(result)

    def test_verdict_score_must_match(self) -> None:
        result = self.valid_result()
        result["score"] = 3
        with self.assertRaisesRegex(ValueError, "uyumsuz"):
            Judge._validate_result(result)

    def test_validation_does_not_semantically_override_calculation(self) -> None:
        result = {
            "reason": "Nihai sonuç farklıdır.",
            "correct_answer": "2.145.780,50 birim",
            "verdict": "Incorrect",
            "score": 1,
            "feedback": "Hesabı yeniden kontrol et.",
        }
        Judge._validate_result(result)
        self.assertEqual(result["verdict"], "Incorrect")
        self.assertEqual(result["correct_answer"], "2.145.780,50 birim")

    def test_evaluate_all_preserves_model_verdict_when_answers_differ(self) -> None:
        model_result = {
            "reason": "Sonuçlar farklıdır.",
            "correct_answer": "47,3821 birim",
            "verdict": "Incorrect",
            "score": 2,
            "feedback": "Nihai sonucu yeniden hesapla.",
        }
        worker_answers = [
            {
                "question_id": 1,
                "question_type": "calculation",
                "question": "Nihai değer nedir?",
                "predicted_answer": "2.145.780,50 birim",
            }
        ]
        with patch.object(self.judge, "evaluate", return_value=model_result):
            result = self.judge.evaluate_all("Kaynak", worker_answers)[0]

        self.assertEqual(result["verdict"], "Incorrect")
        self.assertEqual(result["score"], 2)

    def test_judge_has_no_numeric_auto_correct_implementation(self) -> None:
        source = inspect.getsource(Judge)
        self.assertNotIn("_calculation_answers_match", source)
        self.assertNotIn("worker_numbers", source)
        self.assertNotIn("findall", source)


if __name__ == "__main__":
    unittest.main()
