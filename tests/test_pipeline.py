import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from main import _build_final_results, select_dataset


def attempt(number: int, score: int, verdict: str = "Incorrect") -> dict:
    return {
        "question_id": 1,
        "worker_answer": f"cevap-{number}",
        "verdict": verdict,
        "score": score,
        "feedback": "Tekrar kontrol et.",
        "attempt": number,
    }


class PipelineSelectionTests(unittest.TestCase):
    def test_dataset_menu_is_descriptive_and_mapping_is_preserved(self) -> None:
        output = StringIO()
        with patch("builtins.input", return_value="2"), redirect_stdout(output):
            selected = select_dataset()

        self.assertEqual(selected, "text_2")
        self.assertIn("Fabrika Üretim Raporu", output.getvalue())
        self.assertIn("Finansal İşlem Raporu", output.getvalue())

    def test_scoring_mode_keeps_single_attempt(self) -> None:
        results = _build_final_results({1: [attempt(1, 2)]}, "scoring")
        self.assertEqual(results[0]["attempt_count"], 1)
        self.assertFalse(results[0]["revision_applied"])

    def test_feedback_selects_highest_score(self) -> None:
        attempts = [attempt(1, 2), attempt(2, 7, "Partially Correct"), attempt(3, 3)]
        result = _build_final_results({1: attempts}, "feedback")[0]
        self.assertEqual(result["selected_attempt"], 2)

    def test_score_tie_selects_latest_attempt(self) -> None:
        attempts = [attempt(1, 6, "Partially Correct"), attempt(2, 6, "Partially Correct")]
        result = _build_final_results({1: attempts}, "feedback")[0]
        self.assertEqual(result["selected_attempt"], 2)

    def test_attempt_history_is_preserved(self) -> None:
        attempts = [attempt(1, 1), attempt(2, 2), attempt(3, 3)]
        result = _build_final_results({1: attempts}, "feedback")[0]
        self.assertEqual(len(result["attempt_history"]), 3)


if __name__ == "__main__":
    unittest.main()
