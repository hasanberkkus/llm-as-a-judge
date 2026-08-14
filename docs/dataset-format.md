# Dataset Formatı

Her dataset `data/<dataset_adı>/` altında üç dosyadan oluşur.

## `source_text.txt`

Soruların yanıtlanacağı, boş olmayan UTF-8 kaynak metindir.

## `questions.json`

```json
[
  {
    "id": 1,
    "type": "information_retrieval",
    "question": "..."
  },
  {
    "id": 2,
    "type": "calculation",
    "question": "..."
  }
]
```

`id` değerleri benzersiz tam sayılar; `type` ve `question` boş olmayan metinlerdir.

## `expected_answers.json`

```json
[
  {
    "question_id": 1,
    "expected_answer": "..."
  }
]
```

`question_id` değerleri benzersiz olmalı ve `questions.json` içindeki ID kümesiyle tam eşleşmelidir. Expected Answer yalnızca insan referansı, dataset kontrolü ve raporlama için kullanılır.

