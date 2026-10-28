# mt2-okey

Metin2 Okey Kart Etkinliği için yerel çalışan hamle öneri asistanı. Amacı, oyun sonunda
400+ puanla Altın Okey Sandığı kazanma olasılığını artırmaktır.

Uygulama oyuna bağlanmaz, oyun dosyalarını değiştirmez ve otomasyon yapmaz. Kartlar elle girilir.

- Mimari ve görev planı: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- Kurallar ve doğrulama durumu: [docs/RULES.md](docs/RULES.md)

## Durum

Kart modeli, kurallar ve puanlama motoru tamamlandı ve testleri yazıldı. Oyun durumu,
arayüz ve stratejiler henüz yok (bkz. görev listesi).

## Geliştirme

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```
