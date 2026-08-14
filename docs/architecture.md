# Mimari

`main.py` orchestration katmanıdır ve bağımlılıkları tek yönde kullanır:

```text
main.py
  ├── DatasetLoader
  ├── Worker
  ├── Judge
  └── ReportGenerator
```

Worker Judge'ı, Judge Worker'ı bilmez. DatasetLoader ve ReportGenerator model çağırmaz. Feedback kontrolü yalnızca `main.py` içindedir.

## Scoring akışı

```text
Dataset → Worker → Judge → Report
```

## Feedback akışı

```text
Dataset → Worker → Judge
                    ↓ Correct değilse
          Worker Revision → Judge
                    ↓ Correct değilse
          Worker Revision → Judge
                    ↓
              Best Attempt → Report
```

Judge'a yalnızca kaynak metin, soru ve Worker cevabı gider. Expected Answer model sınırının dışında kalır ve raporda dataset referansı olarak birleştirilir.

