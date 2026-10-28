# mt2-okey

Metin2 Okey Kart Etkinliği için yerel çalışan hamle öneri asistanı. Amacı, oyun sonunda
400+ puanla Altın Okey Sandığı kazanma olasılığını artırmaktır.

Uygulama oyuna bağlanmaz, oyun dosyalarını değiştirmez ve otomasyon yapmaz. Kartlar elle girilir.

- Mimari ve görev planı: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Kurallar ve doğrulama durumu: [docs/RULES.md](docs/RULES.md)

## Durum

Tamamlanan ve test edilenler: kart modeli, kurallar, puanlama motoru, oyun durumu,
geri alınabilir hamle geçmişi, elle kart girişi yapılan Streamlit arayüzü, rastgele ve
açgözlü stratejiler, simülasyon altyapısı ve arayüzde açgözlü hamle önerisi.
Monte Carlo optimizasyonu ve sandık olasılığı tahminleri henüz yok (bkz. görev listesi).

## Çalıştırma

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
streamlit run app/streamlit_app.py
```

Kullanım:
1. Masaya açılan 5 kartı 3×8 tablodan tıklayarak veya "Hızlı giriş" kutusuna
   `K5 M6 S7` biçiminde yazarak girin (K = kırmızı, M = mavi, S = sarı).
   Yanlış girdiğiniz karta tekrar tıklamak onu kaldırır.
2. Oyunda yaptığınız hamleyi seçin (üçlü için 3 kart, atmak için 1 kart) ve onaylayın.
3. Masaya gelen yeni kartları girin. Hatalı onayları kenar çubuğundaki "Geri al" ile düzeltin.

Kenar çubuğunda kaynaklarda net olmayan "üçlü varken kart atmak yasak mı?" kuralını
oyunda gözlemlediğinize göre ayarlayabilirsiniz.

## Geliştirme

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```
