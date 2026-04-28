# 🚗 CarTrack

<p align="center">
  <b>Kurumsal Araç Rezervasyon ve Kullanım Takip Sistemi</b><br>
  Django tabanlı, kullanıcı ekranı + özelleştirilmiş admin panel + scheduler altyapısı
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white">
  <img alt="Django" src="https://img.shields.io/badge/Django-4.2.7-092E20?logo=django&logoColor=white">
  <img alt="DB" src="https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white">
  <img alt="Server" src="https://img.shields.io/badge/WSGI-Waitress-5B3DF5">
  <img alt="Status" src="https://img.shields.io/badge/Status-Active-success">
</p>

> ✨ Bu doküman, projeyi ilk kez kuracak ekip üyeleri ve canlıya çıkaracak kişiler için hazırlanmıştır.

---

## 🧭 Hızlı Menü

- [🚀 Proje Özeti](#-proje-özeti)
- [🏗️ Mimari ve Teknoloji](#️-mimari-ve-teknoloji)
- [⚡ 5 Dakikada Kurulum](#-5-dakikada-kurulum)
- [🔐 Canlıya Çıkış Güvenlik Checklist](#-canlıya-çıkış-güvenlik-checklist)
- [📧 Mail Bildirim + Register Task](#-mail-bildirim--register-task)
- [⏱️ Rezervasyon Job](#️-rezervasyon-job)
- [🌐 Önemli URL'ler](#-önemli-urller)
- [🛠️ Sorun Giderme](#️-sorun-giderme)

---

## 🚀 Proje Özeti

CarTrack tek ekrandan operasyon yönetimi sağlar:

- ✅ Araç durumları: `Müsait`, `Kullanımda/Rezerve`, `Kullanım Dışı`
- 📅 Rezervasyon: oluşturma, iptal, uzatma, bitirme
- 🧾 Teslim formu zorunluluğu (kullanım bitişinde)
- 📍 Kilometre + kullanım bilgisi takibi
- 🛠️ Admin panelinden araç/rezervasyon/kullanıcı/tarihçe yönetimi
- 📤 Excel/TXT export
- 🔔 Muayene/sigorta/kasko tarihleri için otomatik mail bildirimi

### 🎯 Kimler için?

| Rol | Yetki |
|---|---|
| Kullanıcı | Rezervasyon akışları, kullanım tamamlama |
| Yönetici (Admin) | Tüm kayıtlar, export, tarihçe ve doküman yönetimi |

---

## 🏗️ Mimari ve Teknoloji

### 📦 Teknoloji stack

| Katman | Teknoloji |
|---|---|
| Backend | Python 3.11 + Django 4.2.7 |
| Veritabanı | SQLite (varsayılan) |
| WSGI | Waitress |
| Excel | openpyxl |
| PDF | reportlab + pypdf |

### 🗂️ Proje yapısı (özet)

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

### 🧩 Admin modülerliği

- `admin_vehicle.py`
- `admin_reservation.py`
- `admin_usage.py`
- `admin_user.py`

---

## ⚡ 5 Dakikada Kurulum

### 1️⃣ Repoyu klonla

```powershell
git clone <REPO_URL>
cd CarTrack
```

### 2️⃣ Sanal ortam oluştur

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3️⃣ Bağımlılıkları kur

```powershell
pip install -r requirements.txt
```

### 4️⃣ Migration + superuser

```powershell
py -3.11 manage.py migrate
py -3.11 manage.py createsuperuser
```

### 5️⃣ Uygulamayı çalıştır

```powershell
py -3.11 manage.py runserver
```

- 🌍 Uygulama: `http://127.0.0.1:8000/cartrack/`
- 🔐 Admin: `http://127.0.0.1:8000/cartrack/admin/`

---

## 🔐 Canlıya Çıkış Güvenlik Checklist

> ⚠️ `cartrack/settings.py` varsayılanları development içindir. Canlıya bu haliyle çıkmak risklidir.

| Ayar | Zorunlu Değişiklik |
|---|---|
| `SECRET_KEY` | Kendi güçlü anahtarınla değiştir |
| `DEBUG` | `False` yap |
| `ALLOWED_HOSTS` | `*` kullanma, gerçek host/domain gir |
| `CSRF_TRUSTED_ORIGINS` | Gerçek origin listesi ile güncelle |
| `CSRF_COOKIE_SECURE` | HTTPS varsa `True` |
| DB | Yoğun kullanımda PostgreSQL önerilir |

### 🖥️ Canlı servis örneği

```powershell
waitress-serve --listen=127.0.0.1:8000 cartrack.wsgi:application
```

---

## 📧 Mail Bildirim + Register Task

### 1) `.env` dosyası oluştur (proje kökü)

```env
GMAIL_USER=ornek@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
MAIL_RECEIVERS=mail1@firma.com,mail2@firma.com
NOTIFICATION_DAYS=30,15,7,3,1
```

### 2) Görevi oluştur/güncelle

```powershell
py -3.11 register_task.py
```

Bu script:
- 🗓️ `CarTrack Vehicle Notification Job` adında günlük görev oluşturur
- 🕗 Varsayılan saat: `08:00`
- 🧠 Script: `vehicle_notification_job.py`

### 3) Durum kontrol / aç-kapat

```powershell
schtasks /Query /TN "CarTrack Vehicle Notification Job" /FO CSV /NH
schtasks /Change /TN "CarTrack Vehicle Notification Job" /Enable
schtasks /Change /TN "CarTrack Vehicle Notification Job" /Disable
```

---

## ⏱️ Rezervasyon Job

Zamanı gelen rezervasyonları kullanıma çevirir:

```powershell
py -3.11 manage.py process_reservations
```

> 💡 Operasyonel gerçek: Bu komut scheduler ile periyodik çalışmazsa yoğun kullanımda rezervasyon başlangıçlarında gecikme/kaçırma riski oluşur.

---

## 🌐 Önemli URL'ler

- Login: `/cartrack/login/`
- Araç listesi: `/cartrack/vehicles/`
- Admin: `/cartrack/admin/`
- Araç export: `/cartrack/admin/vehicles/vehicle/export/`
- Rezervasyon export: `/cartrack/admin/vehicles/vehiclereservation/export/`
- Kullanım tamamlama: `/cartrack/vehicle/usage/complete/`

---

## 🛠️ Sorun Giderme

### Migration / kolon hatası

```powershell
py -3.11 manage.py migrate
```

### Bağımlılık hatası

```powershell
pip install -r requirements.txt
```

### Scheduler çalışmıyor

- `schtasks /Query` ile görev gerçekten var mı kontrol et.
- Python/script path çözümlemesini doğrula.
- `.env` eksikse mail gönderimi çalışmaz.

---

## 📌 Not

Bu proje şirket içi kullanım için geliştirilmiştir.  
Canlıya açmadan önce güvenlik ayarları ve erişim politikası mutlaka tekrar gözden geçirilmelidir.
