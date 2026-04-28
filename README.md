# CarTrack

CarTrack, şirket araç havuzu için geliştirilmiş bir rezervasyon ve kullanım takip sistemidir.
Uygulama kullanıcı ekranı + özelleştirilmiş Django Admin ile çalışır.

> Bu README, projeyi ilk kez indirip ayağa kaldıracak ekip üyeleri ve canlı ortama çıkaracak kişiler için hazırlanmıştır.

---

## Proje Ne İşe Yarar?

- Araçların anlık durumunu gösterir (`Müsait`, `Kullanımda/Rezerve`, `Kullanım Dışı`).
- Kullanıcıların rezervasyon oluşturma / iptal / uzatma / bitirme işlemlerini yönetir.
- Süresi dolan kullanım için teslim formunu zorunlu kılar.
- Kilometre, kullanım amacı ve rota bilgisini kayıt altına alır.
- Admin panelinden araç, rezervasyon, kullanıcı, araç tarihçesi ve belgeleri yönetir.
- Excel/TXT dışa aktarma ve kritik tarih e-posta bildirimleri sağlar.

---

## Mimari ve Teknoloji

### Teknoloji yığını

- Python 3.11
- Django 4.2.7
- SQLite (varsayılan)
- Waitress (WSGI servis)
- openpyxl (Excel export)
- reportlab + pypdf (PDF işlemleri)

### Mimari yaklaşım

- **Monolit Django yapı**
  - `cartrack/`: proje ayarları ve root URL.
  - `vehicles/`: iş kuralları, modeller, admin modülleri, management komutları.
- **Template tabanlı UI**
  - Kullanıcı ekranları: `templates/vehicles/*`
  - Admin override: `templates/admin/*`
- **Katmanlı admin modülerliği**
  - `admin_vehicle.py`, `admin_reservation.py`, `admin_usage.py`, `admin_user.py`
- **Arka plan işi / scheduler**
  - Windows Task Scheduler için `register_task.py`
  - Bildirim scripti `vehicle_notification_job.py`

---

## Proje Yapısı (Özet)

```text
CarTrack/
├── cartrack/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── vehicles/
│   ├── models.py
│   ├── views.py
│   ├── forms.py
│   ├── middleware.py
│   ├── admin.py
│   ├── admin_vehicle.py
│   ├── admin_reservation.py
│   ├── admin_usage.py
│   ├── admin_user.py
│   └── management/commands/
│       ├── process_reservations.py
│       └── flush_data.py
├── templates/
├── static/
├── vehicle_notification_job.py
├── register_task.py
├── requirements.txt
└── README.md
```

---

## İlk Kurulum (Local)

### 1) Repo klonla

```powershell
git clone <REPO_URL>
cd CarTrack
```

### 2) Sanal ortam oluştur

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3) Bağımlılıkları yükle

```powershell
pip install -r requirements.txt
```

### 4) Veritabanını hazırla

```powershell
py -3.11 manage.py migrate
```

### 5) Admin kullanıcı oluştur

```powershell
py -3.11 manage.py createsuperuser
```

### 6) Uygulamayı çalıştır

```powershell
py -3.11 manage.py runserver
```

- Uygulama: `http://127.0.0.1:8000/cartrack/`
- Admin: `http://127.0.0.1:8000/cartrack/admin/`

---

## Canlı Ortamda Çalıştırma (Minimum)

```powershell
waitress-serve --listen=127.0.0.1:8000 cartrack.wsgi:application
```

> Canlıda genelde Waitress + reverse proxy (Nginx/IIS) kullanılır.

---

## İlk İndirenlerin Mutlaka Değiştirmesi Gerekenler

`cartrack/settings.py` içindeki varsayılanlar geliştirme amaçlıdır. Canlıda bu hali risklidir.

### Zorunlu ayarlar

1. `SECRET_KEY`
   - Mevcut değer örnek/development değeridir.
   - Kendi gizli anahtarını üretip değiştir.

2. `DEBUG`
   - Canlıda `False` olmalı.

3. `ALLOWED_HOSTS`
   - `['*']` bırakmak güvenli değil.
   - Sadece gerçek domain/IP girilmeli.

4. `CSRF_TRUSTED_ORIGINS`
   - Kendi domain/protokolüne göre düzenle.
   - Eski/başkasına ait hostları temizle.

5. `CSRF_COOKIE_SECURE`
   - HTTPS kullanıyorsan `True` yap.

6. Veritabanı
   - Varsayılan SQLite local için uygundur.
   - Çok kullanıcılı canlıda PostgreSQL gibi bir veritabanına geçiş önerilir.

---

## E-posta Bildirimleri (Muayene/Sigorta/Kasko)

Bildirim scripti: `vehicle_notification_job.py`  
Scheduler kaydı: `register_task.py`

### `.env` dosyası oluştur

Proje köküne `.env` ekle:

```env
GMAIL_USER=ornek@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
MAIL_RECEIVERS=mail1@firma.com,mail2@firma.com
NOTIFICATION_DAYS=30,15,7,3,1
```

### Notlar

- `GMAIL_APP_PASSWORD`: normal şifre değil, Gmail App Password olmalı.
- `MAIL_RECEIVERS`: virgülle ayrılmış alıcı listesi.
- `NOTIFICATION_DAYS`: kalan gün eşikleri (örn. `3` => bitime 3 gün kala mail).

---

## Register Task (Windows Task Scheduler)

### Görevi oluştur / güncelle

```powershell
py -3.11 register_task.py
```

Bu komut:
- Görev adı: `CarTrack Vehicle Notification Job`
- Çalışma tipi: günlük
- Saat: `08:00`
- Çalıştırdığı script: `vehicle_notification_job.py`

### Durum kontrol

```powershell
schtasks /Query /TN "CarTrack Vehicle Notification Job" /FO CSV /NH
```

### Enable / Disable

```powershell
schtasks /Change /TN "CarTrack Vehicle Notification Job" /Enable
schtasks /Change /TN "CarTrack Vehicle Notification Job" /Disable
```

---

## Rezervasyon İşleme Komutu

Zamanı gelen rezervasyonlardan kullanım kaydı üretmek için:

```powershell
py -3.11 manage.py process_reservations
```

> Bu komutu da ayrı bir scheduler ile periyodik çalıştırmanız gerekir; aksi halde sadece middleware tetiklerine güvenmek operasyonel olarak yetersiz kalabilir.

---

## Önemli URL’ler

- Login: `/cartrack/login/`
- Araç listesi: `/cartrack/vehicles/`
- Admin: `/cartrack/admin/`
- Araç export: `/cartrack/admin/vehicles/vehicle/export/`
- Rezervasyon export: `/cartrack/admin/vehicles/vehiclereservation/export/`
- Kullanım tamamlama: `/cartrack/vehicle/usage/complete/`

---

## Sık Karşılaşılan Sorunlar

### Migration / kolon hataları

```powershell
py -3.11 manage.py migrate
```

### Bağımlılık hataları

```powershell
pip install -r requirements.txt
```

### Scheduler çalışmıyor

- Görevin oluştuğunu `schtasks /Query` ile doğrula.
- Python path ve script path’in doğru resolve edildiğini kontrol et.
- `.env` yoksa mail gönderimi çalışmaz.

---

## Lisans / Not

Bu proje şirket içi kullanım senaryosu için geliştirilmiştir.  
Canlıya açmadan önce güvenlik ayarlarını ve erişim politikasını yeniden değerlendirmeniz gerekir.
