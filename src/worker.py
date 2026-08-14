import json
from pathlib import Path
from typing import Any

from ollama import ResponseError, chat

from src.config import PROMPTS_DIR, WORKER_MODEL


class Worker:
    """Kaynak metne göre soruları küçük yerel modele yönlendirir."""

    def __init__(
        self,
        model_name: str = WORKER_MODEL,
        prompt_path: str | Path | None = None,
        revision_prompt_path: str | Path | None = None,
    ) -> None:
        self.model_name = model_name
        self.prompt_path = (
            Path(prompt_path)
            if prompt_path is not None
            else PROMPTS_DIR / "worker_prompt.txt"
        )
        self.revision_prompt_path = (
            Path(revision_prompt_path)
            if revision_prompt_path is not None
            else PROMPTS_DIR / "worker_revision_prompt.txt"
        )

        self.prompt_template = self._load_prompt(
            self.prompt_path,
            "Worker",
        )
        self.revision_prompt_template = self._load_prompt(
            self.revision_prompt_path,
            "Worker revision",
        )

    def ask(self, source_text: str, question: str) -> str:
        """Kaynak metne göre tek bir soruyu cevaplatır."""
        self._validate_input(source_text, "Kaynak metin")
        self._validate_input(question, "Soru")

        prompt = self._build_prompt(
            source_text=source_text,
            question=question,
        )

        return self._call_model(prompt)

    def ask_all(
        self,
        source_text: str,
        questions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Tüm soruları sırayla modele gönderir."""
        if not questions:
            raise ValueError("Soru listesi boş olamaz.")

        answers: list[dict[str, Any]] = []
        total_questions = len(questions)

        for question_data in questions:
            question_id = question_data["id"]
            question_type = question_data["type"]
            question = question_data["question"]

            print(
                f"Worker: Soru {question_id}/{total_questions} işleniyor..."
            )

            answer = self.ask(
                source_text=source_text,
                question=question,
            )

            answers.append(
                {
                    "question_id": question_id,
                    "question_type": question_type,
                    "question": question,
                    "predicted_answer": answer,
                }
            )

            print(
                f"Worker: Soru {question_id}/{total_questions} tamamlandı."
            )

        return answers

    def _build_prompt(self, source_text: str, question: str) -> str:
        """Prompt şablonundaki alanları gerçek verilerle doldurur."""
        return self.prompt_template.format(
            source_text=source_text,
            question=question,
        )

    def _call_model(self, prompt: str) -> str:
        """Ollama üzerinden yerel modeli çalıştırır."""
        try:
            response = chat(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                format="json",
                options={
                    "temperature": 0,
                    "num_ctx": 4096,
                    "num_predict": 640,
                    "seed": 42,
                },
            )
        except ResponseError as error:
            raise RuntimeError(
                f"Ollama model hatası: {error}"
            ) from error
        except ConnectionError as error:
            raise RuntimeError(
                "Ollama servisine bağlanılamadı. "
                "Ollama uygulamasının açık olduğunu kontrol et."
            ) from error

        raw_answer = response.message.content.strip()

        if not raw_answer:
            raise ValueError("Worker modeli boş cevap döndürdü.")

        return self._normalize_answer(raw_answer)

    @staticmethod
    def _normalize_answer(raw_answer: str) -> str:
        """JSON biçimli model çıktısından yalnızca nihai cevabı ayıklar."""
        try:
            parsed_answer = json.loads(raw_answer)
        except json.JSONDecodeError:
            return raw_answer

        if not isinstance(parsed_answer, dict):
            return raw_answer

        for field in ("answer", "predicted_answer"):
            value = parsed_answer.get(field)
            if isinstance(value, str) and value.strip():
                return value.strip()

        return raw_answer

    def _load_prompt(self, prompt_path: Path, prompt_name: str) -> str:
        """Prompt şablonunu dosyadan yükler."""
        if not prompt_path.exists():
            raise FileNotFoundError(
                f"{prompt_name} prompt dosyası bulunamadı: {prompt_path}"
            )

        prompt_template = prompt_path.read_text(encoding="utf-8").strip()

        if not prompt_template:
            raise ValueError(f"{prompt_name} prompt dosyası boş olamaz.")

        return prompt_template

    @staticmethod
    def _validate_input(value: str, field_name: str) -> None:
        """Metin girdisinin geçerli olup olmadığını kontrol eder."""
        if not isinstance(value, str):
            raise TypeError(f"{field_name} metin türünde olmalıdır.")

        if not value.strip():
            raise ValueError(f"{field_name} boş olamaz.")

    def revise(
        self,
        source_text: str,
        question: str,
        worker_answer: str,
        feedback: str,
    ) -> str:
        """Judge geri bildirimine göre cevabı yeniden üretir."""
        self._validate_input(source_text, "Kaynak metin")
        self._validate_input(question, "Soru")
        self._validate_input(worker_answer, "İlk Worker cevabı")
        self._validate_input(feedback, "Judge geri bildirimi")

        prompt = self.revision_prompt_template.format(
            source_text=source_text,
            question=question,
            worker_answer=worker_answer,
            feedback=feedback,
        )

        return self._call_model(prompt)
