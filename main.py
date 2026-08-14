from typing import Any

from src.config import JUDGE_MODEL, WORKER_MODEL
from src.dataset import DatasetLoader
from src.judge import Judge
from src.report_generator import ReportGenerator
from src.worker import Worker


def select_dataset() -> str:
    """Kullanıcıdan kullanılacak dataset'i alır."""
    dataset_options = {
        "1": "text_1",
        "2": "text_2",
    }

    while True:
        print(
            "========================================\n"
            "LLM as a Judge - Dataset Selection\n"
            "========================================\n\n"
            "Kullanılacak veri setini seçin:\n\n"
            "1 - Fabrika Üretim Raporu\n"
            "    Üretim, kalite ve fabrika verileri\n\n"
            "2 - Finansal İşlem Raporu\n"
            "    Döviz, komisyon, KDV ve ticari işlemler"
        )

        selection = input("\n\nSeçiminiz (1/2): ").strip()

        if selection in dataset_options:
            return dataset_options[selection]

        print("\nGeçersiz seçim. Lütfen 1 veya 2 girin.\n")


def _select_mode() -> str:
    """Kullanıcıdan çalışma modunu alır."""
    print(
        "Çalışma modunu seçin:\n\n"
        "1 - Yalnızca puanlama\n"
        "2 - Feedback ile düzeltme"
    )

    selection = input("\nSeçiminiz: ").strip()

    if selection not in {"1", "2"}:
        raise ValueError("Çalışma modu 1 veya 2 olmalıdır.")

    return selection


def _build_final_results(
    results_by_question: dict[Any, list[dict[str, Any]]],
    evaluation_mode: str,
) -> list[dict[str, Any]]:
    """Attempt geçmişinden her soru için nihai sonucu seçer."""
    final_results: list[dict[str, Any]] = []

    for attempts in results_by_question.values():
        selected_result = max(
            attempts,
            key=lambda result: (result["score"], result["attempt"]),
        )

        final_results.append(
            {
                **selected_result,
                "evaluation_mode": evaluation_mode,
                "initial_worker_answer": attempts[0]["worker_answer"],
                "initial_verdict": attempts[0]["verdict"],
                "initial_score": attempts[0]["score"],
                "initial_feedback": attempts[0]["feedback"],
                "attempt_count": len(attempts),
                "selected_attempt": selected_result["attempt"],
                "revision_applied": len(attempts) > 1,
                "attempt_history": attempts,
            }
        )

    return final_results


def _validate_final_results(
    final_results: list[dict[str, Any]],
    source_text: str,
) -> None:
    """Rapor öncesinde final sonuçların tutarlılığını doğrular."""
    score_ranges = {
        "Correct": range(9, 11),
        "Partially Correct": range(4, 9),
        "Incorrect": range(0, 4),
    }

    for result in final_results:
        attempts = result["attempt_history"]

        for attempt in attempts:
            Judge.validate_consistency(
                result=attempt,
                source_text=source_text,
            )

        best_attempt = max(
            attempts,
            key=lambda attempt: (attempt["score"], attempt["attempt"]),
        )

        if result["selected_attempt"] != best_attempt["attempt"]:
            raise ValueError("Selected Attempt en iyi attempt değil.")

        if result["score"] not in score_ranges[result["verdict"]]:
            raise ValueError("Final Verdict ile Final Score uyumsuz.")


def main() -> None:
    """LLM-as-a-Judge işlem hattını çalıştırır."""
    try:
        dataset_name = select_dataset()
        mode_selection = _select_mode()
        evaluation_mode = (
            "scoring"
            if mode_selection == "1"
            else "feedback"
        )

        loader = DatasetLoader(
            dataset_name=dataset_name,
        )
        dataset = loader.load_dataset()

        worker = Worker()
        judge = Judge()

        print("\nWorker modeli cevapları üretiyor...\n")

        worker_answers = worker.ask_all(
            source_text=dataset["source_text"],
            questions=dataset["questions"],
        )

        print("\nJudge modeli cevapları değerlendiriyor...\n")

        first_results = judge.evaluate_all(
            source_text=dataset["source_text"],
            worker_answers=worker_answers,
        )

        results_by_question: dict[Any, list[dict[str, Any]]] = {}

        for result in first_results:
            result["attempt"] = 1
            results_by_question[result["question_id"]] = [result]

        if mode_selection == "2":
            pending_results = [
                result
                for result in first_results
                if result["verdict"] != "Correct"
            ]

            for attempt in range(2, 4):
                if not pending_results:
                    break

                print(
                    f"\nWorker modeli {attempt}. attempt cevaplarını "
                    "üretiyor...\n"
                )

                revised_answers: list[dict[str, Any]] = []

                for previous_result in pending_results:
                    revised_answer = worker.revise(
                        source_text=dataset["source_text"],
                        question=previous_result["question"],
                        worker_answer=previous_result["worker_answer"],
                        feedback=previous_result["feedback"],
                    )

                    revised_answers.append(
                        {
                            "question_id": previous_result["question_id"],
                            "question_type": previous_result["question_type"],
                            "question": previous_result["question"],
                            "predicted_answer": revised_answer,
                        }
                    )

                print(
                    f"\nJudge modeli {attempt}. attempt cevaplarını "
                    "değerlendiriyor...\n"
                )

                attempt_results = judge.evaluate_all(
                    source_text=dataset["source_text"],
                    worker_answers=revised_answers,
                )

                pending_results = []

                for result in attempt_results:
                    result["attempt"] = attempt
                    results_by_question[result["question_id"]].append(result)

                    if result["verdict"] != "Correct":
                        pending_results.append(result)

        final_results = _build_final_results(
            results_by_question=results_by_question,
            evaluation_mode=evaluation_mode,
        )
        _validate_final_results(
            final_results=final_results,
            source_text=dataset["source_text"],
        )

        report_generator = ReportGenerator()

        report_generator.generate(
            dataset=dataset,
            results=final_results,
            worker_model=WORKER_MODEL,
            judge_model=JUDGE_MODEL,
            dataset_name=dataset_name,
        )

    except (
        FileNotFoundError,
        TypeError,
        ValueError,
        RuntimeError,
    ) as error:
        print(f"\nProgram çalıştırılırken hata oluştu:\n{error}")


if __name__ == "__main__":
    main()
