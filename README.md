# mt2-okey

Metin2 Okey Kart Etkinliği için yerel çalışan hamle öneri asistanı. Amacı, oyun sonunda
400+ puanla Altın Okey Sandığı kazanma olasılığını artırmaktır.

Kartlar elle girilir. Uygulama oyuna bağlanmaz, oyun dosyalarını değiştirmez ve otomasyon
yapmaz.

## Kurulum ve çalıştırma

Python 3.11 veya üstü gerekir (3.12 önerilir).

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .
streamlit run app/streamlit_app.py
```

Tarayıcıda iki sayfa açılır: **Oyun** ve **Strateji karşılaştırma**.

## Kullanım

1. **Kartları girin.** Masaya açılan 5 kartı 3×8 tablodan tıklayın veya "Hızlı giriş"
   kutusuna `K5 M6 S7` yazın (K = kırmızı, M = mavi, S = sarı). Yanlış girdiğiniz karta
   tekrar tıklamak onu kaldırır.
2. **Öneriyi okuyun.** Masa dolunca her geçerli hamle Monte Carlo ile değerlendirilir.
   Her hamle için şunlar gösterilir:
   - altın ve gümüş sandık olasılığı (%95 aralıklarıyla);
   - beklenen ve medyan oyun sonu puanı;
   - avantajlar ve dezavantajlar.

   En iyi hamle üstte gösterilir; tüm adaylar bir tabloda karşılaştırılabilir.
3. **Yaptığınız hamleyi onaylayın.** "Öneriyi seç" yalnızca kartları seçer. Oyunda ne
   yaptıysanız (önerilen olmak zorunda değil) onu seçip onaylayın.
4. **Yeni gelen kartları girin**, ardından tekrar 2. adıma dönün. Hatalı bir girişi
   kenar çubuğundaki "Geri al" ile düzeltin.

Kenar çubuğu ayarları:
- **Simülasyon sayısı:** Daha fazlası belirsizliği azaltır ama yavaşlatır.
- **Devam stratejisi:** Her aday hamleden sonra oyunun nasıl simüle edileceği.
- **"Üçlü varken kart atmak yasak" kuralı:** Bu kural kaynaklarda net değil. Oyunda
  gözlemlediğinize göre ayarlayın.

## Stratejiler ve ölçülen sonuçlar

| Strateji | Ne yapar |
|---|---|
| Rastgele | Kurallara uygun hamlelerden birini rastgele seçer (karşılaştırma tabanı). |
| Açgözlü | En yüksek anlık puanlı üçlüyü oynar; üçlü yoksa en az işe yarayan kartı atar. |
| Seçici (≥50) | Destede kart varken yalnızca 50+ puanlı üçlüleri oynar, diğer durumlarda kart atar. |
| Monte Carlo | Her hamleyi aynı rastgele deste sıralarıyla sonuna kadar simüle eder; önce altın, sonra gümüş olasılığına, sonra beklenen puana bakar. |

1.000 oyunluk ölçüm, her strateji aynı desteleri oynadı (tohum 2026):

| Strateji | Altın | Gümüş veya üstü | Ortalama puan |
|---|---|---|---|
| Rastgele | %0,0 | %0,0 | 75,5 |
| Açgözlü | %1,3 | %24,1 | 258,9 |
| Seçici (≥50) | %2,6 | %35,2 | 273,8 |
| Monte Carlo (N=100) | **%7,2** | **%67,0** | **310,7** |

Güven aralıkları, bağımsız destelerle tekrar ve diğer ayrıntılar
[docs/BENCHMARKS.md](docs/BENCHMARKS.md) dosyasında. Sonuçları yeniden üretmek için:

```bash
python -m okey.benchmark --games 1000 --seed 2026 --mc-n 100 --workers 4
```

## Önemli sınırlamalar

- **Tahminler kesin değildir.** Gösterilen olasılıklar simülasyon tahminidir ve simüle
  edilen devam stratejisine bağlıdır.
- **Bazı kurallar doğrulanmadı.** Bu kurallar yapılandırılabilir tutuldu; listesi ve
  kaynakları [docs/RULES.md](docs/RULES.md) dosyasında. En önemlileri:
  - masada üçlü varken kart atılabilir mi?
  - puan tablosunun ara değerleri doğru mu?

  Bunlar oyunda kontrol edilmelidir.

## Proje yapısı

```
src/okey/        kurallar, puanlama, oyun durumu, stratejiler, simülasyon, benchmark
app/             Streamlit arayüzü (yalnızca görünüm; oyun mantığı src/okey içinde)
tests/           pytest testleri (arayüz testleri dahil)
docs/            mimari, kurallar, benchmark raporu ve ham sonuçlar
```

Ayrıntılı mimari ve görev geçmişi: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Geliştirme

```bash
pip install -e ".[dev]"
pytest
```

Yeni bir sunucunun puan tablosunu eklemek için `src/okey/rules.py` içindeki `PRESETS`
sözlüğüne yeni bir `RuleConfig` eklemek yeterlidir.
