# Değerlendirme Akışı

Worker, yalnızca kaynak metin ve sorudan kısa bir nihai cevap üretir. Judge, Worker cevabını önce yok sayarak aynı soruyu kaynak metinden bağımsız çözer ve `correct_answer` üretir; ardından iki cevabı karşılaştırır.

Verdict ve score aralıkları:

- `Correct`: 9–10
- `Partially Correct`: 4–8
- `Incorrect`: 0–3

Scoring modunda tek Worker cevabı ve tek Judge değerlendirmesi vardır.

Feedback modunda Correct olmayan cevap Judge feedback'i ile revize edilir. En fazla üç Worker/Judge attempt çalışır ve Correct sonucu alındığında erken durur. Üç attempt sonunda Correct yoksa en yüksek score seçilir; score eşitse attempt numarası daha yüksek olan, yani daha yeni cevap seçilir.

Expected Answer bu akışta değerlendirme veya seçim girdisi değildir.

