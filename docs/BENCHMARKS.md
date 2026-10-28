# Strateji Karşılaştırması (Benchmark)

Aşağıdaki sayıların hepsi `python -m okey.benchmark` çıktısından alınmıştır. Ham
veriler (oyun başına puanlar) `docs/benchmarks/*.json` dosyalarında; uygulamadaki
"Strateji karşılaştırma" sayfası bu dosyaları okur.

## Yöntem

- **Kurallar:** `OFFICIAL_2026` ön ayarı. Bu ön ayar iki doğrulanmamış varsayım içerir
  (bkz. `docs/RULES.md`):
  - masada üçlü varken kart atılabilir (A6);
  - puan tablosunun ara değerleri +10 adımla artar.

  Bu varsayımlar değişirse sonuçlar da değişebilir.
- **Ortak desteler:** Her stratejide i'inci oyun aynı deste sırasıyla oynanır. Bu yüzden
  stratejiler arasındaki farklar **eşleştirilmiş** olarak ölçülür. Eşleştirilmiş farkın
  belirsizliği, iki bağımsız tahminin aralıklarının birleşiminden çok daha dardır.
- **Stratejiler:**
  1. **Rastgele:** Kurallara uygun hamlelerden birini rastgele seçer.
  2. **Açgözlü:** En yüksek anlık puanlı üçlüyü oynar. Üçlü yoksa geleceğe en az
     katkısı olan kartı atar.
  3. **Monte Carlo (N):** Her karar anında her adayı N ortak deste sırasıyla dener.
     Oyunun devamı açgözlü stratejiyle oynanır. Önce altın, sonra gümüş-veya-üstü
     olasılığına göre gürültüye dayanıklı eleme yapar, sonra beklenen puana bakar.
- **Belirsizlik gösterimi:**
  - Oranlar için %95 Wilson aralığı verilir.
  - Ortalama için standart hata (SH) verilir.
  - Farklar için ± 1,96 × eşleştirilmiş standart hata verilir.
- **Süre:** Tek çekirdekte, oyun başına duvar saati süresi. Ölçümler 4 çekirdekli
  bir bulut makinesinde, 4 paralel işçiyle yapıldı. Başka işler aynı anda
  çalıştığı için süreler kabaca alınmalıdır.

## Sonuçlar

### 1. Ana karşılaştırma — 1.000 oyun, tohum 2026, MC N=100

| Strateji | Altın | Altın %95 | Gümüş | Gümüş %95 | Ortalama ± SH | Medyan | sn/oyun |
|---|---|---|---|---|---|---|---|
| Rastgele | %0.0 | %0.0–%0.4 | %0.0 | %0.0–%0.4 | 75.5 ± 1.6 | 70 | 0.0004 |
| Açgözlü | %1.3 | %0.8–%2.2 | %22.8 | %20.3–%25.5 | 258.9 ± 1.8 | 250 | 0.0004 |
| Monte Carlo (N=100) | %7.2 | %5.8–%9.0 | %59.8 | %56.7–%62.8 | 310.7 ± 1.6 | 310 | 1.39 |

Eşleştirilmiş farklar (referans: açgözlü):

| Strateji − Açgözlü | Altın farkı | Gümüş-veya-üstü farkı | Ortalama puan farkı |
|---|---|---|---|
| Rastgele | −1.3 ± 0.7 puan | −24.1 ± 2.7 puan | −183.5 ± 4.4 |
| Monte Carlo (N=100) | +5.9 ± 1.5 puan | +42.9 ± 3.5 puan | +51.7 ± 3.5 |

### 2. Kararlılık: bağımsız desteler — 1.000 oyun, tohum 7, MC N=100

| Strateji | Altın | Altın %95 | Gümüş | Gümüş %95 | Ortalama ± SH | Medyan | sn/oyun |
|---|---|---|---|---|---|---|---|
| Rastgele | %0.0 | %0.0–%0.4 | %0.2 | %0.1–%0.7 | 74.2 ± 1.7 | 70 | 0.0004 |
| Açgözlü | %1.5 | %0.9–%2.5 | %21.9 | %19.4–%24.6 | 258.4 ± 1.7 | 250 | 0.0004 |
| Monte Carlo (N=100) | %8.2 | %6.7–%10.1 | %57.8 | %54.7–%60.8 | 308.8 ± 1.6 | 300 | 1.34 |

| Strateji − Açgözlü | Altın farkı | Gümüş-veya-üstü farkı | Ortalama puan farkı |
|---|---|---|---|
| Rastgele | −1.5 ± 0.8 puan | −23.2 ± 2.6 puan | −184.2 ± 4.5 |
| Monte Carlo (N=100) | +6.7 ± 1.6 puan | +42.6 ± 3.4 puan | +50.5 ± 3.4 |

İki bağımsız deste kümesinde sonuçlar her strateji için birbirinin güven aralığı içinde.

### 3. Kararlılık: büyük örneklem — 10.000 oyun, tohum 2026 (MC yok)

| Strateji | Altın | Altın %95 | Gümüş | Gümüş %95 | Ortalama ± SH | Medyan |
|---|---|---|---|---|---|---|
| Rastgele | %0.0 | %0.0–%0.0 | %0.0 | %0.0–%0.0 | 72.9 ± 0.5 | 70 |
| Açgözlü | %1.3 | %1.1–%1.5 | %22.6 | %21.8–%23.4 | 259.1 ± 0.6 | 260 |

Açgözlü stratejinin 1.000 oyunluk tahminleri (%1.3 altın, %22.8 gümüş) 10.000 oyunluk
daha dar aralıklarla uyumlu.

### 4. Simülasyon sayısının etkisi — 1.000 oyun, tohum 2026, MC N=200

| Strateji | Altın | Altın %95 | Gümüş | Gümüş %95 | Ortalama ± SH | Medyan | sn/oyun |
|---|---|---|---|---|---|---|---|
| Monte Carlo (N=200) | %7.6 | %6.1–%9.4 | %59.3 | %56.2–%62.3 | 310.3 ± 1.6 | 310 | 2.52 |

Aynı destelerde N=200 − N=100 eşleştirilmiş farkları:

| | Fark |
|---|---|
| Altın | +0.4 ± 1.1 puan |
| Gümüş-veya-üstü | −0.1 ± 2.2 puan |
| Ortalama puan | −0.4 ± 1.8 |

Simülasyon sayısını ikiye katlamak süreyi yaklaşık ikiye katlıyor ama sonuçta ölçülebilir
bir iyileşme getirmiyor (farklar sıfırla uyumlu). Bu ayarda darboğaz örneklem sayısı
değil, devam stratejisinin (açgözlü) gücü.

## Yorum

- **Monte Carlo açık ara en iyisi.** Aynı destelerde açgözlüye göre altın sandık
  oranını yaklaşık %1,3–1,5'ten %7–8'e çıkarıyor. Bu, yaklaşık 5 kat demek; fark
  her iki deste kümesinde de belirsizlik aralığının çok üstünde. Gümüş-veya-üstü
  oranını da yaklaşık %24'ten %66–67'ye çıkarıyor.
- **Mutlak altın oranı hâlâ düşük (~%7–8).** Monte Carlo yalnızca bir adım ileriye
  bakıyor; ondan sonrası açgözlü oynanıyor. Daha güçlü bir devam stratejisi (iki
  aşamalı rollout, sezgisel atma kuralları) altın oranını yükseltebilir. Bu, 7.
  aşamadaki iyileştirme adayıdır. Sonuç gerçek oyundaki kurallar doğrulanmadan
  genellenmemelidir.
- **Rastgele strateji neredeyse hiç gümüş/altın görmüyor.** Çünkü rastgele hamleler
  çoğunlukla puansız kart atmak oluyor.
- **N=100 ile N=200 arasında fark ölçülemedi.** Altın, gümüş ve puan farklarının hepsi
  sıfırla uyumlu. Oyun içi öneride daha büyük N, tek bir kararın tahminini daraltır.
  Ancak strateji olarak daha iyi oynamayı sağlamaz.
- **Maliyet:** Monte Carlo (N=100) oyun başına yaklaşık 1,3–1,4 sn sürüyor. Bu,
  karar başına yaklaşık 0,1 sn demek. Arayüzde varsayılan N=500 olduğundan bir karar
  yaklaşık 1 sn sürer.

## Yeniden üretme

```bash
python -m okey.benchmark --games 1000 --seed 2026 --mc-n 100 --workers 4 \
    --json docs/benchmarks/main_seed2026_n1000_mc100.json
python -m okey.benchmark --games 10000 --seed 2026 --mc-n 0 --workers 4 \
    --json docs/benchmarks/baselines_seed2026_n10000.json
python -m okey.benchmark --games 1000 --seed 7 --mc-n 100 --workers 4 \
    --json docs/benchmarks/repeat_seed7_n1000_mc100.json
python -m okey.benchmark --games 1000 --seed 2026 --mc-n 200 --workers 4 \
    --json docs/benchmarks/main_seed2026_n1000_mc200.json
```

Aynı tohum ve kurallarla puanlar birebir aynı çıkar; süreler makineye göre değişir.
