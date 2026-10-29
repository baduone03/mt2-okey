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

Tarayıcıda üç sayfa var: **Oyun** (sade ekran, varsayılan), **Detaylı** ve
**Strateji karşılaştırma**.

## Kullanım (sade ekran)

1. Masaya açılan 5 kartı tablodan işaretle.
2. Ekran tek bir komut verir, örneğin **"AT 8"** veya **"OYNA 3 4 5"**. Önerilen kartlar
   tabloda kalın çerçeveyle gösterilir.
3. Oyunda yap ve **"✓ Yaptım"**a bas.
4. Ekran **"Yerine gelen N kartı işaretle"** der. Yeni gelen kartları işaretle ve
   2. adıma dön.

Düzeltme ve diğer seçenekler:
- Yanlış girdiğin karta tekrar dokunmak onu siler.
- Önerilenden farklı bir şey yaptıysan "Başka bir hamle yaptım" bölümünden seç.
- "Geri al" son adımı geri alır. "Yeni oyun" onay ister.

## Detaylı sayfa

Detaylı sayfa aynı oyunu şu ek bilgilerle gösterir:
- her hamle için altın/gümüş sandık olasılıkları (%95 aralıklarıyla);
- beklenen puan;
- avantaj/dezavantaj açıklamaları.

Kenar çubuğundan şunlar ayarlanır:
- simülasyon sayısı;
- devam stratejisi;
- "üçlü varken kart atmak yasak" kuralı. Bu kural kaynaklarda net değil; oyunda
  gözlemlediğine göre ayarla.

## Stratejiler ve ölçülen sonuçlar

| Strateji | Ne yapar |
|---|---|
| Rastgele | Kurallara uygun hamlelerden birini rastgele seçer (karşılaştırma tabanı). |
| Açgözlü | En yüksek anlık puanlı üçlüyü oynar; üçlü yoksa en az işe yarayan kartı atar. |
| Seçici (≥50) | Destede kart varken yalnızca 50+ puanlı üçlüleri oynar, diğer durumlarda kart atar. |
| Monte Carlo | Her hamleyi aynı rastgele deste sıralarıyla sonuna kadar simüle eder; önce altın, sonra gümüş olasılığına, sonra beklenen puana bakar. |
| **Kahin planı (PIMC)** | Gelecek kartların 20 olası sırasını örnekler. Her biri için oyun sonuna kadar en iyi planı çözer ve 400'e en çok ulaşan hamleyi seçer. **Uygulamanın varsayılan yöntemi.** |

Kahin planı, aynı 300 destede altın oranını mevcut Monte Carlo yönteminin %6,0'ından
%10,7'ye çıkardı (eşleştirilmiş fark +4,7 ± 2,9 puan); gümüş oranı aynı kaldı (%70).
Deste sırasını önceden bilen kusursuz bir oyuncunun tavanı bu destelerde yaklaşık %30
altın.

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
