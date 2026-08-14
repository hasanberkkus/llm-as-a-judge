import json
from pathlib import Path
from typing import Any

from ollama import ResponseError, chat

from src.config import JUDGE_MODEL, PROMPTS_DIR


class Judge:
    """Worker cevaplarını bağımsız değerlendirmeyle inceler."""

    MAX_GENERATION_ATTEMPTS = 3

    def __init__(
        self,
        model_name: str = JUDGE_MODEL,
        prompt_path: str | Path | None = None,
    ) -> None:
        self.model_name = model_name
        self.prompt_path = (
            Path(prompt_path)
            if prompt_path is not None
            else PROMPTS_DIR / "judge_prompt.txt"
        )
        self.prompt_template = self._load_prompt(
            self.prompt_path,
            "Judge",
        )

    def evaluate(
        self,
        source_text: str,
        question: str,
        worker_answer: str,
    ) -> dict[str, Any]:
        """Soruyu çözer ve Worker cevabını tek çağrıda değerlendirir."""
        self._validate_input(source_text, "Kaynak metin")
        self._validate_input(question, "Soru")
        self._validate_input(worker_answer, "Worker cevabı")

        prompt = self._build_prompt(
            source_text=source_text,
            question=question,
            worker_answer=worker_answer,
        )
        return self._generate_validated_result(
            prompt=prompt,
            validator=self._validate_result,
        )

    def evaluate_all(
        self,
        source_text: str,
        worker_answers: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Tüm Worker cevaplarını sırayla değerlendirir."""
        if not worker_answers:
            raise ValueError("Worker cevap listesi boş olamaz.")

        results: list[dict[str, Any]] = []
        total_answers = len(worker_answers)

        for index, answer in enumerate(worker_answers, start=1):
            print(
                f"Judge: Soru {index}/{total_answers} değerlendiriliyor..."
            )
            result = self.evaluate(
                source_text=source_text,
                question=answer["question"],
                worker_answer=answer["predicted_answer"],
            )
            print(f"Judge: Soru {index}/{total_answers} tamamlandı.")

            results.append(
                {
                    "question_id": answer["question_id"],
                    "question_type": answer["question_type"],
                    "question": answer["question"],
                    "correct_answer": result["correct_answer"],
                    "worker_answer": answer["predicted_answer"],
                    "verdict": result["verdict"],
                    "score": result["score"],
                    "reason": result["reason"],
                    "feedback": result["feedback"],
                }
            )

        return results

    def _build_prompt(
        self,
        source_text: str,
        question: str,
        worker_answer: str,
    ) -> str:
        """Tek aşamalı Judge promptunu oluşturur."""
        return self.prompt_template.format(
            source_text=source_text,
            question=question,
            worker_answer=worker_answer,
        )

    def _generate_validated_result(self, prompt: str, validator: Any) -> dict[str, Any]:
        """Geçersiz model çıktısını sahte sonuç üretmeden yeniden dener."""
        validation_error: ValueError | None = None

        for _ in range(self.MAX_GENERATION_ATTEMPTS):
            retry_prompt = prompt
            if validation_error is not None:
                retry_prompt += (
                    "\n\nÖNCEKİ ÇIKTI GEÇERSİZDİ:\n"
                    f"{validation_error}\n"
                    "Yalnızca istenen alanlarla geçerli JSON döndür."
                )

            try:
                result = self._call_model(retry_prompt)
                validator(result)
            except ValueError as error:
                validation_error = error
                continue
            return result

        raise ValueError(
            "Judge geçerli bir sonuç üretemedi. "
            f"Son doğrulama hatası: {validation_error}"
        )

    def _call_model(self, prompt: str) -> dict[str, Any]:
        """Ollama üzerinden Judge modelini çalıştırır."""
        try:
            response = chat(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                format="json",
                options={
                    "temperature": 0,
                    "num_ctx": 4096,
                    "num_predict": 1024,
                    "repeat_penalty": 1.2,
                    "repeat_last_n": 128,
                    "seed": 42,
                },
                think=False,
            )
        except ResponseError as error:
            raise RuntimeError(
                f"Ollama Judge model hatası: {error}"
            ) from error
        except ConnectionError as error:
            raise RuntimeError(
                "Ollama servisine bağlanılamadı. "
                "Ollama uygulamasının açık olduğunu kontrol et."
            ) from error

        raw_answer = response.message.content.strip()
        if not raw_answer:
            raise ValueError("Judge modeli boş cevap döndürdü.")

        try:
            result = json.loads(raw_answer)
        except json.JSONDecodeError as error:
            raise ValueError(
                "Judge modeli geçerli JSON döndürmedi.\n"
                f"Model çıktısı:\n{raw_answer}"
            ) from error
        return result

    @classmethod
    def _validate_result(cls, result: Any) -> None:
        """Birleştirilmiş Judge sonucunun yapısını doğrular."""
        if not isinstance(result, dict):
            raise ValueError("Judge sonucu bir JSON nesnesi olmalıdır.")

        required_fields = {
            "correct_answer",
            "verdict",
            "score",
            "reason",
            "feedback",
        }
        missing_fields = required_fields - result.keys()
        if missing_fields:
            raise ValueError(
                f"Judge sonucunda eksik alanlar var: {missing_fields}"
            )

        for field in {"correct_answer", "verdict", "reason", "feedback"}:
            if not isinstance(result[field], str) or not result[field].strip():
                raise ValueError(f"{field} boş olmayan metin olmalıdır.")

        cls._validate_verdict_score_and_feedback(result)

    @classmethod
    def _validate_verdict_score_and_feedback(
        cls,
        result: dict[str, Any],
    ) -> None:
        """Verdict, score ve feedback sözleşmesini doğrular."""
        verdict = result["verdict"]
        valid_verdicts = {"Correct", "Partially Correct", "Incorrect"}
        if verdict not in valid_verdicts:
            raise ValueError(f"Geçersiz verdict: {verdict}")

        score = result["score"]
        if isinstance(score, bool) or not isinstance(score, int):
            raise ValueError("Judge puanı tam sayı olmalıdır.")

        score_ranges = {
            "Correct": range(9, 11),
            "Partially Correct": range(4, 9),
            "Incorrect": range(0, 4),
        }
        if score not in score_ranges[verdict]:
            raise ValueError("Verdict ile score uyumsuz.")

        feedback = result["feedback"].strip()
        if verdict == "Correct":
            if feedback != "Düzeltme gerekmiyor.":
                raise ValueError("Correct verdict için feedback geçersiz.")
        elif feedback == "Düzeltme gerekmiyor.":
            raise ValueError("Correct olmayan verdict düzeltme istemelidir.")

    @classmethod
    def validate_consistency(
        cls,
        result: dict[str, Any],
        source_text: str,
    ) -> None:
        """Kaydedilecek bir attempt sonucunun yapısını doğrular."""
        del source_text
        cls._validate_result(result)

    @staticmethod
    def _load_prompt(prompt_path: Path, prompt_name: str) -> str:
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
