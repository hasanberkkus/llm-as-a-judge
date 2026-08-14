import json
import tempfile
import unittest
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from src.config import DATA_DIR, PROMPTS_DIR
from src.dataset import DatasetLoader


class DatasetLoaderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.dataset_dir = self.root / "text_1"
        self.dataset_dir.mkdir()
        (self.dataset_dir / "source_text.txt").write_text(
            "Kaynak", encoding="utf-8"
        )
        self._write_json(
            "questions.json",
            [{"id": 1, "type": "calculation", "question": "Soru?"}],
        )
        self._write_json(
            "expected_answers.json",
            [{"question_id": 1, "expected_answer": "Cevap"}],
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _write_json(self, name: str, value: object) -> None:
        (self.dataset_dir / name).write_text(
            json.dumps(value, ensure_ascii=False), encoding="utf-8"
        )

    def test_loads_valid_dataset(self) -> None:
        dataset = DatasetLoader("text_1", self.root).load_dataset()
        self.assertEqual(dataset["source_text"], "Kaynak")
        self.assertEqual(dataset["questions"][0]["id"], 1)

    def test_missing_file_fails(self) -> None:
        (self.dataset_dir / "source_text.txt").unlink()
        with self.assertRaises(FileNotFoundError):
            DatasetLoader("text_1", self.root).load_dataset()

    def test_empty_source_fails(self) -> None:
        (self.dataset_dir / "source_text.txt").write_text("", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "boş"):
            DatasetLoader("text_1", self.root).load_dataset()

    def test_invalid_json_fails(self) -> None:
        (self.dataset_dir / "questions.json").write_text("{", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Geçersiz JSON"):
            DatasetLoader("text_1", self.root).load_dataset()

    def test_duplicate_question_id_fails(self) -> None:
        self._write_json(
            "questions.json",
            [
                {"id": 1, "type": "calculation", "question": "Bir?"},
                {"id": 1, "type": "calculation", "question": "İki?"},
            ],
        )
        with self.assertRaisesRegex(ValueError, "benzersiz"):
            DatasetLoader("text_1", self.root).load_dataset()

    def test_question_and_answer_ids_must_match(self) -> None:
        self._write_json(
            "expected_answers.json",
            [{"question_id": 2, "expected_answer": "Cevap"}],
        )
        with self.assertRaisesRegex(ValueError, "eşleşmiyor"):
            DatasetLoader("text_1", self.root).load_dataset()


class Text2DatasetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dataset = DatasetLoader("text_2", DATA_DIR).load_dataset()

    def test_contains_five_questions_of_each_type(self) -> None:
        questions = self.dataset["questions"]
        self.assertEqual(len(questions), 10)
        self.assertEqual(
            [question["type"] for question in questions[:5]],
            ["information_retrieval"] * 5,
        )
        self.assertEqual(
            [question["type"] for question in questions[5:]],
            ["calculation"] * 5,
        )

    def test_question_and_expected_answer_ids_match(self) -> None:
        question_ids = {item["id"] for item in self.dataset["questions"]}
        answer_ids = {
            item["question_id"] for item in self.dataset["expected_answers"]
        }
        self.assertEqual(question_ids, set(range(1, 11)))
        self.assertEqual(answer_ids, question_ids)

    def test_calculation_expected_answers_are_deterministic(self) -> None:
        value = Decimal
        dollar_rate = value("47.3821")
        other_rate = value("53.0056")
        calculated = [
            value("742350.80") / other_rate,
            value("48750.40") + value("915620.45") / dollar_rate,
            value("11450.60")
            * (value("1") - value("0.0135"))
            * dollar_rate
            / other_rate,
            value("387450.75") * (value("1") + value("0.2040")),
            (
                value("387450.75") * (value("1") + value("0.2040"))
                - value("64825.50") * (value("1") + value("0.2040"))
                + value("146780.35")
            ),
        ]
        rounded = [
            item.quantize(value("0.01"), rounding=ROUND_HALF_UP)
            for item in calculated
        ]
        self.assertEqual(
            rounded,
            [
                value("14005.14"),
                value("68074.58"),
                value("10097.59"),
                value("466490.70"),
                value("535221.15"),
            ],
        )
        answers = {
            item["question_id"]: item["expected_answer"]
            for item in self.dataset["expected_answers"]
        }
        self.assertEqual(
            [answers[index] for index in range(6, 11)],
            [
                "14.005,14 avro",
                "68.074,58 Amerikan doları",
                "10.097,59 avro",
                "466.490,70 Türk lirası",
                "535.221,15 Türk lirası",
            ],
        )

    def test_runtime_prompts_do_not_copy_text2_specific_content(self) -> None:
        prompts = "\n".join(
            path.read_text(encoding="utf-8")
            for path in PROMPTS_DIR.glob("*.txt")
        )
        forbidden_fragments = {
            "XYZ Dış Ticaret",
            "12 Ağustos 2026",
            "742.350,80",
            "47,3821",
            "53,0056",
            "Amerikan doları",
            "Türk lirası",
            "avro",
            "KDV",
        }
        for fragment in forbidden_fragments:
            self.assertNotIn(fragment, prompts)


if __name__ == "__main__":
    unittest.main()
