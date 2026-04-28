# CarTrack

<p>
  <b>Kurumsal Araç Rezervasyon ve Kullanım Takip Sistemi</b><br>
  Django tabanlı, kullanıcı ekranı + özelleştirilmiş admin panel + scheduler altyapısı.
</p>

<p>
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11-blue">
  <img alt="Django" src="https://img.shields.io/badge/Django-4.2.7-0C4B33">
  <img alt="DB" src="https://img.shields.io/badge/DB-SQLite-lightgrey">
  <img alt="Server" src="https://img.shields.io/badge/WSGI-Waitress-5B3DF5">
</p>

> Bu doküman, projeyi ilk kez kuracak ekip üyeleri ve canlıya çıkaracak kişiler için hazırlanmıştır.

---

## İçindekiler

- [1) Proje Özeti](#1-proje-özeti)
- [2) Mimari](#2-mimari)
- [3) Hızlı Başlangıç](#3-hızlı-başlangıç)
- [4) Canlıya Çıkış Checklist](#4-canlıya-çıkış-checklist)
- [5) Mail Bildirim ve Register Task](#5-mail-bildirim-ve-register-task)
- [6) Rezervasyon Job](#6-rezervasyon-job)
- [7) Önemli URL’ler](#7-önemli-urller)
- [8) Sorun Giderme](#8-sorun-giderme)

---

## 1) Proje Özeti

CarTrack aşağıdaki operasyonları tek yerden yönetir:

- Araç durumları: `Müsait`, `Kullanımda/Rezerve`, `Kullanım Dışı`
- Rezervasyon: oluşturma, iptal, uzatma, bitirme
- Teslim formu zorunluluğu (kullanım bitişinde)
- Kilometre ve kullanım bilgisi takibi
- Admin panelinden araç/rezervasyon/kullanıcı/tarihçe yönetimi
- Excel/TXT export
- Muayene/sigorta/kasko tarihleri için mail bildirimi

---

## 2) Mimari

### Teknoloji

| Katman | Teknoloji |
|---|---|
| Backend | Python 3.11 + Django 4.2.7 |
| DB | SQLite (varsayılan) |
| WSGI | Waitress |
| Export | openpyxl |
| PDF | reportlab + pypdf |

### Klasör yapısı (özet)

```text
CarTrack/
├── cartrack/                # settings, urls, wsgi
├── vehicles/                # app, modeller, view'lar, admin modülleri
├── templates/               # kullanıcı + admin template override
├── static/                  # css, görseller
├── register_task.py         # windows task scheduler kaydı
├── vehicle_notification_job.py
└── requirements.txt
```

### Admin modülerliği

- `admin_vehicle.py`
- `admin_reservation.py`
- `admin_usage.py`
- `admin_user.py`

---

## 3) Hızlı Başlangıç

### Adım 1 - Repoyu klonla

```powershell
git clone <REPO_URL>
cd CarTrack
```

### Adım 2 - Sanal ortam oluştur

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
```

### Adım 3 - Paketleri kur

```powershell
pip install -r requirements.txt
```

### Adım 4 - Migration

```powershell
py -3.11 manage.py migrate
```

### Adım 5 - Superuser oluştur

```powershell
py -3.11 manage.py createsuperuser
```

### Adım 6 - Çalıştır

```powershell
py -3.11 manage.py runserver
```

- Uygulama: `http://127.0.0.1:8000/cartrack/`
- Admin: `http://127.0.0.1:8000/cartrack/admin/`

---

## 4) Canlıya Çıkış Checklist

`cartrack/settings.py` içindeki varsayılanlar development amaçlıdır.  
Canlıya almadan önce aşağıdakiler **zorunlu**:

| Ayar | Gerekli Değer |
|---|---|
| `SECRET_KEY` | Kendi güçlü anahtarın |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | Sadece gerçek host/domain |
| `CSRF_TRUSTED_ORIGINS` | Gerçek origin listesi |
| `CSRF_COOKIE_SECURE` | HTTPS varsa `True` |
| DB | Yoğun kullanımda SQLite yerine PostgreSQL önerilir |

Canlı servis örneği:

```powershell
waitress-serve --listen=127.0.0.1:8000 cartrack.wsgi:application
```

---

## 5) Mail Bildirim ve Register Task

### `.env` dosyası (proje kökü)

```env
GMAIL_USER=ornek@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
MAIL_RECEIVERS=mail1@firma.com,mail2@firma.com
NOTIFICATION_DAYS=30,15,7,3,1
```

### Register Task

```powershell
py -3.11 register_task.py
```

Bu script:
- `CarTrack Vehicle Notification Job` adında günlük görev oluşturur/günceller
- Varsayılan saat: `08:00`
- Çalıştırdığı script: `vehicle_notification_job.py`

Durum kontrol:

```powershell
schtasks /Query /TN "CarTrack Vehicle Notification Job" /FO CSV /NH
```

Enable / Disable:

```powershell
schtasks /Change /TN "CarTrack Vehicle Notification Job" /Enable
schtasks /Change /TN "CarTrack Vehicle Notification Job" /Disable
```

---

## 6) Rezervasyon Job

Zamanı gelen rezervasyonlardan kullanım kaydı üretir:

```powershell
py -3.11 manage.py process_reservations
```

> Operasyonel not: Bu komutu scheduler ile periyodik çalıştırmazsan sadece anlık tetikleyicilere güvenmiş olursun; yoğun kullanımda gecikme/kaçırma riski oluşur.

---

## 7) Önemli URL’ler

- Login: `/cartrack/login/`
- Araç listesi: `/cartrack/vehicles/`
- Admin: `/cartrack/admin/`
- Araç export: `/cartrack/admin/vehicles/vehicle/export/`
- Rezervasyon export: `/cartrack/admin/vehicles/vehiclereservation/export/`
- Kullanım tamamlama: `/cartrack/vehicle/usage/complete/`

---

## 8) Sorun Giderme

### Migration / kolon hatası

```powershell
py -3.11 manage.py migrate
```

### Bağımlılık hatası

```powershell
pip install -r requirements.txt
```

### Scheduler çalışmıyor

- Görevin varlığını `schtasks /Query` ile doğrula.
- Python/script path çözümlemesini kontrol et.
- `.env` eksikse mail gönderimi çalışmaz.

---

## Not

Bu proje şirket içi kullanım için geliştirilmiştir.  
Canlıya açmadan önce güvenlik ayarları ve erişim politikası tekrar gözden geçirilmelidir.
