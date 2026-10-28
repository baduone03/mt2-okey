# Mimari

## 1. Hedef ve sınırlar

- Kullanıcı masadaki kartları **elle** girer. Uygulama en iyi hamleyi önerir.
- Asıl amaç **P(skor ≥ 400)** değerini, yani Altın Okey Sandığı olasılığını en yüksek yapmaktır.
  İkincil amaç P(skor ≥ 300), sonra beklenen skordur.
- Tamamen yerel çalışır. Oyuna bağlanmaz, oyun dosyalarına dokunmaz, otomasyon yapmaz.
- Kurallar `docs/RULES.md` belgesine bağlıdır. Belirsiz kurallar `RuleConfig` alanı olarak tutulur.

## 2. Katmanlar

```
┌───────────────────────────────────────────────┐
│ app/ (Streamlit)  sadece görünüm + oturum      │  ← tek Streamlit bağımlılığı burada
├───────────────────────────────────────────────┤
│ okey.session      olay günlüğü, geri al        │
│ okey.advisor      öneri üretimi (UI'dan bağımsız)│
├───────────────────────────────────────────────┤
│ okey.strategies   random / greedy / monte_carlo │
│ okey.simulation   oyun oynatma, ortak rastgele  │
│ okey.stats        Wilson aralığı, özetler       │
├───────────────────────────────────────────────┤
│ okey.state        GameState + Action + apply()  │
│ okey.combos       170 üçlünün ön hesabı, puan   │
│ okey.rules        RuleConfig, ön ayarlar         │
│ okey.cards        Color, Card, bitmask yardımcıları│
└───────────────────────────────────────────────┘
```

Bağımlılık yönü yalnızca aşağı doğrudur. `okey` paketi Streamlit'i import etmez,
bu yüzden kurallar, algoritma ve arayüz ayrı ayrı test edilebilir.

## 3. Dosya yapısı

```
mt2-okey/
├── pyproject.toml            # paket, bağımlılıklar (streamlit), dev: pytest
├── README.md                 # kurulum + çalıştırma
├── docs/
│   ├── ARCHITECTURE.md
│   ├── RULES.md              # doğrulanmış/belirsiz kurallar
│   ├── BENCHMARKS.md         # ölçülen sonuçlar ve yorum
│   └── benchmarks/           # ham çıktı: *.json (oyun başına puanlar) + *.md tablolar
├── src/okey/
│   ├── __init__.py
│   ├── cards.py              # Color, Card, ALL_CARDS, card<->index<->bit, parse("K5")
│   ├── rules.py              # RuleConfig (frozen dataclass), OFFICIAL_2026, Chest, chest_for()
│   ├── combos.py             # ComboKind, Combo, ALL_COMBOS (170), classify(), score()
│   ├── state.py              # GameState (frozen), Play/Discard/Draw, legal_actions(), apply()
│   ├── session.py            # olay günlüğü (event log), undo, replay, tutarlılık kontrolü
│   ├── simulation.py         # play_out(state, policy, deck_order) ; CRN tohum üretimi
│   ├── stats.py              # wilson_interval, mean_se, summary
│   ├── advisor.py            # recommend(state, cfg) -> list[Recommendation]
│   ├── strategies/
│   │   ├── base.py           # Policy Protocol: choose(state, rng) -> Action
│   │   ├── random_policy.py
│   │   ├── greedy.py
│   │   └── monte_carlo.py    # rollout tabanlı Strateji B
│   └── benchmark.py          # python -m okey.benchmark --games 1000 --seed 1
├── app/
│   ├── streamlit_app.py      # giriş noktası + sayfa gezinmesi (Oyun / Strateji karşılaştırma)
│   └── views/
│       ├── game_page.py      # oyun sayfası
│       ├── state.py          # st.session_state sarmalayıcısı
│       ├── sidebar.py        # geri al, yeni oyun, kural ayarları
│       ├── card_grid.py      # 3×8 tıklanabilir tablo + hızlı metin girişi
│       ├── game_panel.py     # puan, kalan, atılan, görülmemiş, hamle onayı
│       ├── recommendations.py # öneri paneli (avantaj/dezavantaj)
│       ├── history.py
│       └── compare.py        # strateji karşılaştırma ekranı (kayıtlı raporlar + canlı çalıştırma)
└── tests/
    ├── test_cards.py
    ├── test_combos.py        # 170 üçlü, tüm puanlar, geçersiz üçlüler
    ├── test_state.py         # tekrar kullanım engeli, sayım, terminal durum
    ├── test_session.py       # undo = önceki durum (eşitlik), replay tutarlılığı
    ├── test_board.py         # tıklama mantığı
    ├── test_app.py           # Streamlit AppTest ile başsız uçtan uca arayüz testleri
    ├── test_rules.py         # sandık sınıfları, sınır değerler 290/299/300/399/400
    ├── test_simulation.py    # tekrarsız dağıtım, CRN tekrarlanabilirliği
    ├── test_strategies.py    # greedy doğruluğu
    ├── test_monte_carlo.py   # kesin mod = kaba kuvvet, MC ≥ greedy, CRN
    ├── test_advisor.py
    ├── test_stats.py
    ├── test_benchmark.py
    └── test_compare_page.py
```

## 4. Veri modeli

**Kart:** 24 kart, `0..23` indeksiyle temsil edilir (`index = color·8 + (number−1)`).
Kart kümeleri 24 bitlik tamsayı maskelerdir. Böylece "bu üçlü masada mı?" sorusu tek
bir işlemle cevaplanır: `combo.mask & hand == combo.mask`. Kullanıcıya dönük API ise
`Card(color, number)` nesneleriyle çalışır.

**RuleConfig (frozen dataclass):**
`hand_size=5`, puan tabloları (liste), `chest_thresholds`,
`discard_requires_no_combo`, `refill_policy`. Belirsiz kurallar burada yaşar ve
`UNVERIFIED_RULES` sözlüğüyle arayüze bildirilir. Üçlü boyutu (3) ve numara aralığı (1–8)
sabittir.

**GameState (frozen):**
- `hand` (masadaki kartlar)
- `played` (oynanan üçlüler; sıra korunur)
- `discarded`
- `score`

Türetilen alanlar:
- `unseen = ALL − hand − played − discarded`
- `deck_remaining = len(unseen)`

Gerçek oyunda desteden gelen kart, kullanıcı girene kadar bilinmez. Bu nedenle
"görülmemiş" ile "destede kalan" aynı kümedir. Değişmez nesneler, geri almayı ve
simülasyonu güvenli kılar.

**Eylemler:**

| Eylem | Ne yapar |
|---|---|
| `Draw(card)` | Gözlem: desteden gelen kartı masaya ekler |
| `Play(combo)` | Masadaki üç kartı oynar |
| `Discard(card)` | Masadaki bir kartı atar |

`apply(state, action, cfg)` saf bir fonksiyondur. Geçersiz bir eylemde
`IllegalActionError` fırlatır ve mesajında nedeni açıkça yazar.

**Oturum (event sourcing):** Arayüz durumu doğrudan değiştirmez. Olay listesine
ekleme yapar ve durum `fold(apply, events)` ile hesaplanır.
- Geri almak, son olayı listeden çıkarmaktır.
- Kart sayımı ile puanın geçmişle her zaman tutarlı kalması yapısal olarak garanti edilir.
- Testler, geri alma sonrası durumun önceki durumla birebir eşit olduğunu doğrular.

**Aşamalar (phase):**

| Durum | Aşama |
|---|---|
| `len(hand) < hand_size` ve destede kart var | `AWAITING_DRAW`: kullanıcı yeni gelen kart(lar)ı girer, öneri yapılmaz |
| Masa dolu | `DECIDE` |
| Deste boş ve masada üçlü yok | `FINISHED` |

## 5. Algoritmalar

**Strateji 0 – Rastgele:** Kurallara uygun eylemlerden düzgün dağılımla birini seçer.

**Strateji A – Açgözlü:** En yüksek anlık puanlı üçlüyü oynar. Eşitlikleri
deterministik bir kuralla bozar. Üçlü yoksa en "işe yaramaz" kartı atar. Bu ilk
sürümde basit bir sezgiseldir: kartın, görülmemiş kartlarla oluşturabileceği
potansiyel üçlülerin toplam puanı en düşük olan atılır. Atma sezgiseli ayrıca test edilir.

**Strateji B – Monte Carlo rollout (bir adım politika iyileştirme):**

1. Her aday eylem `a` için (tüm geçerli üçlüler + izin veriliyorsa tüm atmalar):
   - `N` adet görülmemiş-kart permütasyonu örneklenir.
   - **Tüm adaylar aynı `N` permütasyonu kullanır** (common random numbers).
     Böylece adaylar arasındaki fark gürültüden değil, eylemden kaynaklanır.
   - Her permütasyon için `a` uygulanır, ardından oyun bir **rollout politikası**
     (varsayılan: açgözlü) ile sonuna kadar oynanır.
2. Her aday için şu ölçümler hesaplanır:
   - `P(altın)` ve `P(gümüş)`: Wilson %95 aralığıyla birlikte
   - `E[skor]` ve standart hatası
   - medyan skor
3. Sıralama gürültüye dayanıklı sözlükseldir:
   - Altın olasılığı en yüksek adaydan eşleştirilmiş farkla anlamlı biçimde
     (z = 1,96) kötü olan adaylar elenir.
   - Kalanlar arasında gümüş-veya-üstü olasılığı için aynı eleme yapılır.
   - Kalanlar arasından beklenen puanı en yüksek olan seçilir.
   - En iyiden ayırt edilemeyen adaylar "≈ en iyi" diye işaretlenir.
   - Kalan kart sayısının tüm sıraları bütçeye sığıyorsa (k! ≤ N) hepsi denenir.
     Bu durumda sonuç devam politikasına göre kesindir ve eleme saf sözlükseldir.
4. Sonuç her zaman şu bilgilerle birlikte gösterilir:
   - simülasyon sayısı
   - güven aralığı
   - kullanılan rollout politikası

   Sonuç kesin olasılık olarak sunulmaz.

Rollout algoritmasının teorik özelliği: Yeterli örneklemde temel politikadan
(açgözlü) beklentide kötü olamaz. Bu iddia benchmark ile **ölçülerek** doğrulanır.

**Performans planı (ölçüm sonrası, gerektiği kadar):**
1. Bitmask ve önceden hesaplanmış üçlü listesiyle saf Python
2. Adaylar arasında erken eleme (successive halving)
3. Rollout önbelleği
4. İsteğe bağlı derinlik sınırlı expectimax + MC yaprak değerlendirmesi

Durum uzayı tam DP için büyük olabilir. Önce ölçülür, sonra karar verilir.

## 6. Arayüz akışı

1. "Yeni oyun" seçilir, kullanıcı ilk 5 kartı 3×8 tablodan tıklayarak girer.
2. `DECIDE` aşamasında öneriler tablo halinde gösterilir. En iyi öneri vurgulanır.
   Her satırda şunlar yer alır:
   - kartlar
   - anlık puan
   - P(altın) ± aralık
   - P(gümüş)
   - E[skor]
   - N
   - avantaj/dezavantaj metni
3. Kullanıcı oyunda yaptığı hamleyi seçip **onaylar**. Bu, önerilen hamle olmak zorunda değildir.
4. Ardından yeni gelen kartlar girilir (`AWAITING_DRAW`).
5. "Geri al" son olayı siler, "Yeni oyun" günlüğü temizler.

Kurallar:
- Tıklanan kart başka bir bölgedeyse (oynanmış/atılmış) tıklama reddedilir.
- Masadaki bir karta ikinci kez tıklamak, o son girişi geri alır.
- Klavye girişi için `cards.parse("K5 M6 S7")` hazırdır (K=kırmızı, M=mavi, S=sarı).
  Bu girişin arayüze bağlanması sonraki bir iştir.

## 7. Bağımlılıklar

- Çalışma zamanı: `streamlit`
- Geliştirme: `pytest`

Başka bağımlılık eklenmez. Rastgelelik `random.Random(seed)` ile, istatistik saf
Python ile yapılır.

## 8. Görev listesi (MVP'ye kadar küçük adımlar)

Her adım: kod + test + `pytest` yeşil. Test edilmeyen özellik "tamamlandı" sayılmaz.

| # | Görev | Kabul ölçütü |
|---|---|---|
| 1.1 ✅ | `pyproject.toml`, paket iskeleti, pytest ayarı | `pytest` boş da olsa çalışır |
| 1.2 ✅ | `cards.py`: Color, Card, indeks/bit dönüşümü, `parse()` | 24 benzersiz kart, gidiş-dönüş testleri |
| 1.3 ✅ | `rules.py`: RuleConfig, OFFICIAL_2026, `chest_for()` | Sınır testleri: 0, 290, 299, 300, 399, 400 |
| 1.4 ✅ | `combos.py`: 170 üçlü, sınıflandırma, puan | Sayılar 8/18/144; tüm puanlar tabloyla eşleşir; geçersiz üçlüler reddedilir |
| 2.1 ✅ | `state.py`: GameState, eylemler, `apply()`, `legal_actions()` | Tekrar kullanım ve kayıp kart engellenir, sayım ve puan doğru güncellenir, terminal durum doğru belirlenir |
| 3.1 ✅ | `session.py`: olay günlüğü, undo, replay | Undo sonrası durum öncekiyle eşit, rastgele olay dizilerinde tutarlılık |
| 3.2 ✅ | Streamlit: kart tablosu + oyun paneli + geçmiş | Elle uçtan uca bir oyun girilebilir |
| 4.1 ✅ | `strategies/greedy.py` + `random_policy.py` | Elle hesaplanmış senaryolarda doğru seçim |
| 4.2 ✅ | `simulation.py`: `play_out`, CRN tohumları | Tekrarsız dağıtım, aynı tohum → aynı oyun |
| 4.3 ✅ | Arayüzde açgözlü öneri | — |
| 5.1 ✅ | `stats.py` + `strategies/monte_carlo.py` | Küçük senaryolarda MC sıralaması ile kaba kuvvet sonucu tutarlı |
| 5.2 ✅ | `advisor.py` + öneri tablosu (P, aralık, N, gerekçe) | — |
| 6.1 ✅ | `benchmark.py` | Aynı başlangıç tohumlarıyla 3 strateji × ≥1000 oyun |
| 6.2 ✅ | Karşılaştırma ekranı + `docs/BENCHMARKS.md` | Sonuçlar script çıktısından alınır |
| 7.x | Profil çıkar → erken eleme / önbellek / expectimax; README | Ölçülen hızlanma raporlanır |
