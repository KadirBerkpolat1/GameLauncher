# GameLauncher

Linux'ta Steam oyun ve DLC yönetimi icin gelistirilmis masaustu uygulamasi. Oyunlari arayip bul, tek tikla DLC'leri sec, manifest dosyalarini otomatik yapilandir ve dogrudan indir.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![Qt](https://img.shields.io/badge/PySide6-Qt6-41CD52?logo=qt&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Linux-FCC624?logo=linux&logoColor=black)

---

## Ozellikler

### Oyun Arama ve Kesif
- **HubcapManifest** API ile oyun katalogu uzerinden arama
- **Steam Web API** ile her oyunun tum DLC listesini otomatik cekme
- Kapak gorselleri ve detaylarla zenginlestirilmis oyun kartlari

### Tek Tikla DLC Yonetimi
- Bir oyunu sectikten sonra tum DLC'leri gorsel listede goruntuleme
- Kurmak istedigin DLC'leri tikla-sec, gerisini uygulama halleder
- SLSsteam `config.yaml` dosyasina AppID ve DLC verilerini otomatik yazma

### Esnek Indirme Motorlari
- **Steam Protokolu** (`steam://install/`): Standart Steam istemcisi uzerinden indirme
- **DepotDownloaderMod**: Bagimsiz olarak manifest bazli depot indirme (Steam disinda)
- Ayarlardan tek tikla motor degistirme

### SLSsteam Entegrasyonu
- GitHub releases'tan **hazir derlenmmis** `.7z` arsivini indirip otomatik kurulum (`setup.sh`)
- `config.yaml` yapilandirmasini arayuzden yonetme (Family Share, Cloud Saves, Game Updates vb.)
- Kurulum durumu tespiti ve tek tikla guncelleme/kaldirma
- Flatpak ve yerel Steam kurulumlarini otomatik algilama

### Manifest Kaynaklari
- **Ryuu API**: API anahtariyla manifest + decryption key ZIP dosyasi cekme
- **Discord Scraper**: Self-bot tokeniyle Discord uzerinden SteamTools botundan manifest toplama
- Manifest dosyalarini otomatik olarak Steam `depotcache` dizinine yerlestirme

### Arayuz
- PySide6 (Qt6) ile tamamen karanlik temalı (Dark Theme) modern arayuz
- Kenar cubugu navigasyonu: Kutuphane, Arama, Indirmeler, Ayarlar
- Steam'i uygulama icinden yeniden baslatma (VDF degisikliklerinin uygulanmasi icin)

---

## Sistem Gereksinimleri

| Gereksinim | Aciklama |
|---|---|
| **Python 3.11+** | Ana calisma ortami |
| **p7zip** | SLSsteam kurulumu icin (`7z` komutu) |
| **Steam** | Yerel veya Flatpak kurulumu |
| .NET 8.0+ Runtime | *(Opsiyonel)* DepotDownloaderMod kullanimi icin |

---

## Kurulum

### Hizli Kurulum (Onerilen)

```bash
git clone https://github.com/KadirBerkpolat1/GameLauncher.git
cd GameLauncher
./install.sh
```

Betik su adimlari otomatik uygular:
1. Python surum kontrolu (3.11+)
2. Sistem bagimlilik kontrolu (7z)
3. Dosyalari `~/.local/share/GameLauncher/` dizinine kopyalar
4. Python sanal ortami olusturur ve bagimliklikari kurar
5. `gamelauncher` komutunu ve masaustu kisayolunu olusturur

Kurulum tamamlandiktan sonra:
```bash
gamelauncher
```

### Manuel Kurulum (Gelistiriciler icin)

```bash
git clone https://github.com/KadirBerkpolat1/GameLauncher.git
cd GameLauncher
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 src/main.py
```

---

## Kaldirma

```bash
./uninstall.sh
```

Betik uygulamayi, komut satirini ve masaustu kisayolunu temizler. Ayar dosyalarini silip silmemeyi sorar.

> **Not:** SLSsteam ayri bir yazilimdir ve bu betik tarafindan kaldirilmaz.
> SLSsteam'i kaldirmak icin: `~/.local/share/SLSsteam/setup.sh uninstall`

---

## Ilk Calistirmada Yapilacaklar

1. Uygulamayi acin ve sol menueden **Settings** tiklayin
2. **Steam Path** alaninin dogru oldugunu kontrol edin (otomatik tespit edilir)
3. Manifest kaynagi olarak **Ryuu API Key** girin
4. *(Opsiyonel)* SLSsteam bolumunden **Install / Update** butonuyla SLSsteam'i kurun
5. *(Opsiyonel)* DDMod bolumunden **Install / Update DDMod** butonuyla DepotDownloader'i kurun

---

## Mimari

```
src/
├── api/                  # Dis servis istemcileri
│   ├── hubcap.py         # HubcapManifest API
│   ├── ryuu_api.py       # Ryuu manifest API
│   ├── steam_web.py      # Steam Store API (DLC listesi)
│   ├── discord_scraper.py # Discord self-bot manifest cekici
│   └── steam.py          # Steam dosya sistemi islemleri
├── config/               # Yapilandirma yoneticileri
│   ├── settings.py       # Uygulama ayarlari (JSON)
│   └── slssteam.py       # SLSsteam config.yaml yonetimi
├── services/             # Is mantigi
│   ├── installer.py      # SLSsteam & DDMod kurulum motoru
│   └── download.py       # Indirme yoneticisi (Steam / DDMod)
├── ui/                   # PySide6 arayuz bilesenleri
│   ├── main_window.py    # Ana pencere ve navigasyon
│   ├── search_widget.py  # Oyun arama ekrani
│   ├── library_widget.py # Kutuphane gorunumu
│   ├── downloads_widget.py # Indirme kuyrugu
│   ├── settings_dialog.py  # Ayarlar penceresi
│   ├── game_card.py      # Oyun karti bileseni
│   ├── dlc_dialog.py     # DLC secim penceresi
│   └── styles.py         # Karanlik tema CSS
├── utils/                # Yardimci araclar
│   ├── paths.py          # Steam/SLSsteam yol tespiti
│   └── vdf_manager.py    # Valve VDF dosya islemleri
├── app.py                # Qt + asyncio entegrasyonu
└── main.py               # Giris noktasi
```

---

## Bagimlilklar

```
PySide6>=6.5.0    # Qt6 arayuz cercevesi
httpx>=0.24.0     # Asenkron HTTP istemcisi
PyYAML>=6.0.1     # SLSsteam config.yaml islemleri
vdf>=3.4          # Valve Data Format okuma/yazma
```

---

## Lisans

Bu proje su an ozel (private) olarak gelistirilmektedir.
