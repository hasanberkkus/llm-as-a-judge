import json
from pathlib import Path
from typing import Any

from src.config import DATA_DIR


class DatasetLoader:
    """Projenin metin, soru ve beklenen cevap verilerini yükler."""

    def __init__(
        self,
        dataset_name: str = "text_1",
        data_directory: str | Path = DATA_DIR,
    ) -> None:
        valid_dataset_names = {"text_1", "text_2"}

        if dataset_name not in valid_dataset_names:
            raise ValueError(
                f"Geçersiz dataset adı: {dataset_name}"
            )

        self.dataset_directory = Path(data_directory) / dataset_name

        self.source_text_path = (
            self.dataset_directory / "source_text.txt"
        )
        self.questions_path = (
            self.dataset_directory / "questions.json"
        )
        self.expected_answers_path = (
            self.dataset_directory / "expected_answers.json"
        )

    def load_source_text(self) -> str:
        """Kaynak metni dosyadan okuyup döndürür."""
        self._validate_file_exists(self.source_text_path)

        text = self.source_text_path.read_text(
            encoding="utf-8"
        ).strip()

        if not text:
            raise ValueError("Kaynak metin boş olamaz.")

        return text

    def load_questions(self) -> list[dict[str, Any]]:
        """Soruları JSON dosyasından okuyup doğrular."""
        questions = self._load_json_file(self.questions_path)

        if not isinstance(questions, list):
            raise ValueError(
                "Sorular bir liste biçiminde olmalıdır."
            )

        if not questions:
            raise ValueError("Soru listesi boş olamaz.")

        self._validate_questions(questions)

        return questions

    def load_expected_answers(self) -> list[dict[str, Any]]:
        """Beklenen cevapları JSON dosyasından okuyup doğrular."""
        expected_answers = self._load_json_file(
            self.expected_answers_path
        )

        if not isinstance(expected_answers, list):
            raise ValueError(
                "Beklenen cevaplar bir liste biçiminde olmalıdır."
            )

        if not expected_answers:
            raise ValueError(
                "Beklenen cevap listesi boş olamaz."
            )

        self._validate_expected_answers(expected_answers)

        return expected_answers

    def load_dataset(self) -> dict[str, Any]:
        """Tüm veri setini tek bir sözlük içinde döndürür."""
        source_text = self.load_source_text()
        questions = self.load_questions()
        expected_answers = self.load_expected_answers()

        self._validate_dataset_consistency(
            questions=questions,
            expected_answers=expected_answers,
        )

        return {
            "source_text": source_text,
            "questions": questions,
            "expected_answers": expected_answers,
        }

    def _load_json_file(self, file_path: Path) -> Any:
        """JSON dosyasını okuyup Python nesnesine dönüştürür."""
        self._validate_file_exists(file_path)

        try:
            with file_path.open("r", encoding="utf-8") as file:
                return json.load(file)

        except json.JSONDecodeError as error:
            raise ValueError(
                f"Geçersiz JSON biçimi: {file_path}\n"
                f"Satır: {error.lineno}, sütun: {error.colno}"
            ) from error

    @staticmethod
    def _validate_questions(
        questions: list[dict[str, Any]],
    ) -> None:
        """Soru nesnelerinin yapısını doğrular."""
        required_fields = {
            "id",
            "type",
            "question",
        }

        question_ids: list[Any] = []

        for index, question in enumerate(questions, start=1):
            if not isinstance(question, dict):
                raise ValueError(
                    f"{index}. soru bir JSON nesnesi olmalıdır."
                )

            missing_fields = required_fields - question.keys()

            if missing_fields:
                raise ValueError(
                    f"{index}. soruda eksik alanlar var: "
                    f"{missing_fields}"
                )

            question_id = question["id"]
            question_type = question["type"]
            question_text = question["question"]

            if isinstance(question_id, bool) or not isinstance(
                question_id,
                int,
            ):
                raise ValueError(
                    f"{index}. sorunun id alanı tam sayı olmalıdır."
                )

            if not isinstance(question_type, str):
                raise ValueError(
                    f"{index}. sorunun type alanı metin olmalıdır."
                )

            if not question_type.strip():
                raise ValueError(
                    f"{index}. sorunun type alanı boş olamaz."
                )

            if not isinstance(question_text, str):
                raise ValueError(
                    f"{index}. sorunun question alanı metin olmalıdır."
                )

            if not question_text.strip():
                raise ValueError(
                    f"{index}. sorunun question alanı boş olamaz."
                )

            question_ids.append(question_id)

        if len(question_ids) != len(set(question_ids)):
            raise ValueError(
                "Soru ID'leri benzersiz olmalıdır."
            )

    @staticmethod
    def _validate_expected_answers(
        expected_answers: list[dict[str, Any]],
    ) -> None:
        """Beklenen cevap nesnelerinin yapısını doğrular."""
        required_fields = {
            "question_id",
            "expected_answer",
        }

        answer_ids: list[Any] = []

        for index, answer in enumerate(
            expected_answers,
            start=1,
        ):
            if not isinstance(answer, dict):
                raise ValueError(
                    f"{index}. beklenen cevap bir JSON nesnesi "
                    "olmalıdır."
                )

            missing_fields = required_fields - answer.keys()

            if missing_fields:
                raise ValueError(
                    f"{index}. beklenen cevapta eksik alanlar var: "
                    f"{missing_fields}"
                )

            question_id = answer["question_id"]
            expected_answer = answer["expected_answer"]

            if isinstance(question_id, bool) or not isinstance(
                question_id,
                int,
            ):
                raise ValueError(
                    f"{index}. beklenen cevabın question_id alanı "
                    "tam sayı olmalıdır."
                )

            if not isinstance(expected_answer, str):
                raise ValueError(
                    f"{index}. beklenen cevabın expected_answer "
                    "alanı metin olmalıdır."
                )

            if not expected_answer.strip():
                raise ValueError(
                    f"{index}. beklenen cevabın expected_answer "
                    "alanı boş olamaz."
                )

            answer_ids.append(question_id)

        if len(answer_ids) != len(set(answer_ids)):
            raise ValueError(
                "Beklenen cevapların question_id değerleri "
                "benzersiz olmalıdır."
            )

    @staticmethod
    def _validate_file_exists(file_path: Path) -> None:
        """Dosyanın mevcut ve geçerli bir dosya olduğunu kontrol eder."""
        if not file_path.exists():
            raise FileNotFoundError(
                f"Gerekli veri dosyası bulunamadı: {file_path}"
            )

        if not file_path.is_file():
            raise ValueError(
                f"Belirtilen yol bir dosya değil: {file_path}"
            )

    @staticmethod
    def _validate_dataset_consistency(
        questions: list[dict[str, Any]],
        expected_answers: list[dict[str, Any]],
    ) -> None:
        """Sorular ile beklenen cevapların tutarlılığını doğrular."""
        if len(questions) != len(expected_answers):
            raise ValueError(
                "Soru sayısı ile beklenen cevap sayısı "
                "eşit olmalıdır."
            )

        question_ids = {
            question["id"]
            for question in questions
        }

        answer_ids = {
            answer["question_id"]
            for answer in expected_answers
        }

        if question_ids != answer_ids:
            missing_answer_ids = question_ids - answer_ids
            unknown_answer_ids = answer_ids - question_ids

            raise ValueError(
                "Soru ID'leri ile cevap ID'leri eşleşmiyor. "
                f"Cevabı bulunmayan soru ID'leri: "
                f"{sorted(missing_answer_ids)}. "
                f"Sorusu bulunmayan cevap ID'leri: "
                f"{sorted(unknown_answer_ids)}."
            )
