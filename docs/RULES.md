# Oyun Kuralları ve Doğrulama Durumu

Bu belge, Metin2 Okey Kart Etkinliği kurallarını **kaynağıyla birlikte** listeler.
Her kural üç durumdan birindedir:

| Durum | Anlamı |
|---|---|
| ✅ Doğrulandı | Resmî Gameforge wiki'sinde açıkça yazıyor ve en az bir bağımsız kaynakla tutarlı. |
| 🟡 Kısmen doğrulandı | Birden fazla topluluk kaynağında tutarlı, ancak resmî metin bu oturumda tam okunamadı. |
| ❓ Belirsiz | Kaynaklarda açık değil. Kod bunu **yapılandırılabilir** tutar ve arayüz kullanıcıya bildirir. |

> Not: Resmî wiki sayfaları (`*-wiki.metin2.gameforge.com`) geliştirme ortamının ağ
> politikası nedeniyle doğrudan açılamadı. Bilgiler arama motoru alıntıları ve
> topluluk kaynaklarından derlendi. Belirsiz satırlar oyun içinde kontrol edilmeli.

## 1. Kartlar

| # | Kural | Durum | Kaynak |
|---|---|---|---|
| K1 | Üç renk: kırmızı, mavi, sarı | ✅ | Resmî wiki, topluluk tabloları |
| K2 | Her renkte 1–8 numaralı kartlar, toplam 24 farklı kart, her kart tek kopya | ✅ (oyun içi: 5 kart açıkken destede 19) | Fan klonu ve yardımcı araçlar "24 kartlık deste" der. Resmî wiki'deki "24 kart toplayınca Okey Kart Seti" ifadesi koleksiyon eşiğidir, deste boyutunu doğrudan söylemez |
| K3 | Oyuna giriş: 30.000 Yang + 1 Okey Kart Seti, seviye 70+ | ✅ | Resmî wiki (optimizasyonu etkilemez, sadece bilgi) |

## 2. Oyun akışı

| # | Kural | Durum | Not |
|---|---|---|---|
| A1 | Desteye tıklayınca masaya 5 rastgele kart açılır | ✅ | Resmî wiki |
| A2 | Bir hamlede masadaki 3 kart seçilip oynanır | ✅ | Resmî wiki |
| A3 | Uygun kart yoksa bir kart sağ tıkla atılır | ✅ | Resmî wiki |
| A4 | Oynanan/atılan kartlar desteye geri dönmez | 🟡 | Tüm kaynaklar ve 24 kartlık sayım bununla tutarlı |
| A5 | Masa desteye tıklanarak **elle** doldurulur; birden fazla kart atıp sonra çekmek mümkündür | ✅ (oyun içi gözlem) | Model her hamleden sonra hemen çeker. Bu en iyi oyundur: kartlar birer birer atılıp hemen çekilirse sonraki karar daha fazla bilgiyle verilir; toplu atmanın avantajı yoktur (deste sırası değişmez). |
| A6 | Kombinasyon **varken** de kart atılabilir | ✅ (oyun içi: üçlü varken de X düğmeleri etkin) | **Stratejiyi en çok etkileyen belirsizlik.** Resmî metin "uygun kart yoksa" der; arayüzün bunu zorlayıp zorlamadığı bilinmiyor. `discard_requires_no_combo` (varsayılan: `False`, yani her zaman atılabilir) |
| A7 | Oyun, deste bittiğinde ve masada oynanabilir üçlü kalmadığında biter | 🟡 (oyun içi: "Bitir" düğmesiyle istenince bitirilebilir; puan azalmadığı için strateji değişmez) | Atmanın puanı yoktur. Bu yüzden "masada kart kalsa da biter" ile "son kart atılınca biter" aynı skoru verir. Modelde terminal durum: `deste boş VE masada geçerli üçlü yok` |

## 3. Geçerli kombinasyonlar

| # | Kural | Durum |
|---|---|---|
| C1 | Aynı numara, üç farklı renk (ör. K5-M5-S5) | ✅ |
| C2 | Ardışık üç numara, aynı renk (ör. K3-K4-K5) | ✅ |
| C3 | Ardışık üç numara, karışık renk (ör. K3-M4-K5). Ardışık seride renk serbesttir ("different or indifferent colours"). | ✅ |
| C4 | Seride boşluk olamaz, döngü (7-8-1) yoktur | ✅ ("no gap") / döngü yok 🟡 |

Kombinasyon uzayı küçüktür ve önceden hesaplanır:
- Aynı numara üçlüsü: 8 (her numarada her renkten tek kart var)
- Seri: 6 başlangıç × 3³ renk ataması = 162 (18 aynı renk + 144 karışık)
- **Toplam: 170 geçerli üçlü**

## 4. Puan tablosu

Varsayılan değerler (`rules.py` içinde `OFFICIAL_2026` ön ayarı):

| Kombinasyon | Formül | Değerler |
|---|---|---|
| Aynı numara n-n-n | `10·n + 10` | 1-1-1 = 20 … 8-8-8 = 90 |
| Aynı renk seri s..s+2 | `10·s + 40` | 1-2-3 = 50 … 6-7-8 = 100 |
| Karışık renk seri s..s+2 | `10·s` | 1-2-3 = 10 … 6-7-8 = 60 |

| Durum | Kaynak |
|---|---|
| ✅ Uç değerler (20/90, 50/100, 10/60) | Resmî EN ve TR wiki alıntıları, topluluk tabloları |
| 🟡 Aradaki değerlerin her adımda +10 arttığı | Topluluk tablolarında tutarlı; karışık 3-4-5 = 30 oyunda doğrulandı. Diğer satırlar tek tek görülmedi |

Puan tablosu **veri** olarak tutulur (formül değil): her kombinasyon tipi için 8 veya 6
elemanlı bir liste. Farklı sunucular için yeni ön ayar eklemek tek satırdır.

## 5. Ödül sandıkları

| Sandık | Eşik | Durum |
|---|---|---|
| Altın | ≥ 400 | ✅ |
| Gümüş | 300–399 | ✅ |
| Bronz | < 300 | ✅ (eski FR wiki "1–290" der) |

Tüm puanlar 10'un katı olduğu için "≤ 290" ile "≤ 299" aynı sonucu verir; bu bir
çelişki değildir. Eşikler `RuleConfig.chest_thresholds` içinde yapılandırılabilir.
Etkinlik sürümleri (Yaz / "Merry" kış) aynı eşikleri kullanıyor görünüyor.

## 6. Oyunda kontrol edilmesi gerekenler

Aşağıdakileri oyunda bir kez gözlemlemek modeli kesinleştirir:

Oyun içinde doğrulananlar:
- K2: 5 kart açıkken destede 19 kart var.
- A5: Masa elle doldurulur.
- A6: Masada üçlü varken de kart atılabilir.
- Puan tablosu ara değeri: karışık seri 3-4-5 = 30.

Hâlâ yalnızca varsayım olan: puan tablosunun diğer ara satırları (+10 adım). Uç değerler
resmî kaynaklarda, 3-4-5 karışık seri oyunda doğrulandı.

## Kaynaklar

- Metin2 Wiki (EN) – Okey Card Game: https://en-wiki.metin2.gameforge.com/index.php/Okey_Card_Game
- Metin2 Wiki (TR) – Okey Etkinliği (Yaz): https://tr-wiki.metin2.gameforge.com/index.php/Okey_Etkinli%C4%9Fi_(Yaz)
- Metin2 Wiki (FR) – Jeu de cartes Okey: https://fr-wiki.metin2.gameforge.com/index.php/Jeu_de_cartes_Okey
- Metin2 Wiki (EN) – Golden Okey Chest: https://en-wiki.metin2.gameforge.com/index.php/Golden_Okey_Chest
- Topluluk: https://forum.gamer.com.tr/konu/metin2-okey-nasil-oynanir.455472/ , https://www.yazilimaktif.com/metin2-okey-kart-seti-nedir/
- Fan klonu (ikincil): https://github.com/Jakbor32/Okey-Card-Game-Clone
