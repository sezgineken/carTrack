from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date


class User(AbstractUser):
    """Extended User model with role field"""
    ROLE_CHOICES = [
        ('USER', 'Personel'),
        ('MANAGER', 'Müdür'),
    ]
    
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='USER',
        verbose_name='Rol'
    )
    duty = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        verbose_name='Görev',
    )
    
    class Meta:
        verbose_name = 'Kullanıcı'
        verbose_name_plural = 'Kullanıcılar'
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"
    
    def is_manager(self):
        return self.role == 'MANAGER'

    @staticmethod
    def _capitalize_words(value: str | None) -> str | None:
        if value is None:
            return value
        return " ".join(word[:1].upper() + word[1:].lower() for word in value.split())

    def save(self, *args, **kwargs):
        self.first_name = self._capitalize_words(self.first_name)
        self.last_name = self._capitalize_words(self.last_name)
        self.duty = self._capitalize_words(self.duty)
        super().save(*args, **kwargs)


class Vehicle(models.Model):
    """Vehicle model"""
    LOCATION_CHOICES = [
        ('Ataşehir', 'Ataşehir'),
        ('Dilovası', 'Dilovası'),
        ('Tuzla', 'Tuzla'),
        ('Santis Plaza', 'Santis Plaza'),
    ]
    OPERATIONAL_STATUS_CHOICES = [
        ('ACTIVE', 'Aktif'),
        ('PASSIVE', 'Pasif'),
    ]
    OWNERSHIP_CHOICES = [
        ('PERSONAL', 'Şahsi'),
        ('RENTAL', 'Kiralık'),
    ]
    plate = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Plaka'
    )
    brand_model = models.CharField(
        max_length=100,
        verbose_name='Marka/Model'
    )
    initial_kilometer = models.IntegerField(
        default=0,
        verbose_name='Başlangıç Kilometresi',
        help_text='Aracın sisteme eklenirkenki kilometresi (ilk kullanımda bu değer kullanılır)'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Aktif'
    )
    show_in_pool = models.BooleanField(
        default=True,
        verbose_name='Araç, havuzda listelensin mi?'
    )
    operational_status = models.CharField(
        max_length=10,
        choices=OPERATIONAL_STATUS_CHOICES,
        default='ACTIVE',
        verbose_name='Araç Durumu',
    )
    ownership = models.CharField(
        max_length=10,
        choices=OWNERSHIP_CHOICES,
        default='PERSONAL',
        verbose_name='Araç Aidiyeti',
    )
    location = models.CharField(
        max_length=20,
        choices=LOCATION_CHOICES,
        default='Ataşehir',
        verbose_name='Lokasyon',
    )
    photo = models.ImageField(
        upload_to='vehicles/',
        null=True,
        blank=True,
        verbose_name='Araç Fotoğrafı',
    )
    
    class Meta:
        verbose_name = 'Araç'
        verbose_name_plural = 'Araçlar'
        ordering = ['location', 'plate']
    
    def __str__(self):
        return f"{self.plate} - {self.brand_model}"
    
    def is_available(self):
        """Check if vehicle is currently available (only checks current usage, not reservations)"""
        if self.operational_status == 'PASSIVE':
            return False
        # Check active usage only - reservations don't block availability for future bookings
        return not self.vehicleusage_set.filter(dropoff_time__isnull=True).exists()
    
    def is_reserved_now(self):
        """Check if vehicle has an active reservation right now"""
        now = timezone.now()
        return self.vehiclereservation_set.filter(
            start_time__lte=now,
            end_time__gte=now,
            is_active=True
        ).exists()
    
    def get_current_usage(self):
        """Get current active usage if exists"""
        return self.vehicleusage_set.filter(dropoff_time__isnull=True).select_related('user').first()
    
    def get_upcoming_reservations(self):
        """Get upcoming reservations for this vehicle"""
        now = timezone.now()
        return self.vehiclereservation_set.filter(
            start_time__gte=now,
            is_active=True
        ).select_related('user').order_by('start_time')
    
    def get_active_reservation(self):
        """Get currently active reservation if exists"""
        now = timezone.now()
        return self.vehiclereservation_set.filter(
            start_time__lte=now,
            end_time__gte=now,
            is_active=True
        ).select_related('user').first()


class VehicleReservation(models.Model):
    """Vehicle reservation model"""
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        verbose_name='Araç'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Kullanıcı'
    )
    start_time = models.DateTimeField(
        verbose_name='Başlangıç Zamanı'
    )
    end_time = models.DateTimeField(
        verbose_name='Bitiş Zamanı'
    )
    purpose = models.TextField(
        null=True,
        blank=True,
        verbose_name='Amaç'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Aktif'
    )
    is_late_return = models.BooleanField(
        default=False,
        verbose_name='Gecikmeli Dönüş',
    )
    is_no_show = models.BooleanField(
        default=False,
        verbose_name='Gelmedi',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Oluşturulma Zamanı'
    )
    
    class Meta:
        verbose_name = 'Araç Rezervasyonu'
        verbose_name_plural = 'Araç Rezervasyonları'
        ordering = ['start_time']
    
    def __str__(self):
        return f"{self.vehicle.plate} - {self.user.get_full_name()} ({self.start_time})"
    
    def clean(self):
        """Validate reservation rules"""
        errors = {}
        
        # End time must be after start time
        if self.end_time and self.start_time and self.end_time <= self.start_time:
            errors['end_time'] = 'Bitiş zamanı başlangıç zamanından sonra olmalıdır.'
        
        # Start time must be in the future (for new reservations)
        if self.pk is None and self.start_time and self.start_time <= timezone.now():
            errors['start_time'] = 'Rezervasyon başlangıç zamanı gelecekte olmalıdır.'
        
        # Check for overlapping reservations (only if vehicle is set)
        if self.vehicle_id and self.start_time and self.end_time:
            if self.vehicle and self.vehicle.operational_status == 'PASSIVE':
                errors['start_time'] = 'Araç şu anda kullanım dışıdır. Rezervasyon yapılamaz.'

            # Same user cannot have overlapping reservations across different vehicles.
            user_overlapping = VehicleReservation.objects.filter(
                user=self.user,
                is_active=True,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time,
            ).exclude(pk=self.pk if self.pk else None)
            if user_overlapping.exists():
                errors['start_time'] = 'Aynı zamana farklı bir randevunuz bulunmaktadır.'

            overlapping = VehicleReservation.objects.filter(
                vehicle=self.vehicle,
                is_active=True,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time
            ).exclude(pk=self.pk if self.pk else None)
            
            if overlapping.exists():
                errors['start_time'] = 'Bu tarih aralığında başka bir rezervasyon var.'

            active_usage = VehicleUsage.objects.filter(
                vehicle=self.vehicle,
                dropoff_time__isnull=True
            ).select_related('reservation').first()
            if active_usage:
                # Hard stop: if previous reservation ended but handover form is not completed,
                # block all new reservations until dropoff is submitted.
                if (
                    active_usage.reservation
                    and active_usage.reservation.end_time
                    and active_usage.reservation.end_time <= timezone.now()
                ):
                    errors['start_time'] = (
                        'Araç için teslim formu bekleniyor. Yeni rezervasyon için önce mevcut kullanımın teslim formu tamamlanmalıdır.'
                    )
                # If active usage is tied to reservation, block until that reservation end.
                elif (
                    active_usage.reservation
                    and active_usage.reservation.end_time
                    and self.start_time < active_usage.reservation.end_time
                ):
                    errors['start_time'] = (
                        f'Araç şu anda kullanımda. En erken '
                        f'{active_usage.reservation.end_time:%d.%m.%Y %H:%M} sonrası rezervasyon yapabilirsiniz.'
                    )
                # If active usage has no reservation linkage, do not allow past/current start.
                elif self.start_time <= timezone.now():
                    errors['start_time'] = 'Araç şu anda kullanımda. Mevcut kullanım bitmeden rezervasyon yapılamaz.'
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def is_current(self):
        """Check if reservation is currently active"""
        now = timezone.now()
        return self.is_active and self.start_time <= now <= self.end_time
    
    def is_upcoming(self):
        """Check if reservation is upcoming"""
        return self.is_active and self.start_time > timezone.now()


class VehicleUsage(models.Model):
    """Vehicle usage tracking model"""
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        verbose_name='Araç'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Kullanıcı'
    )
    pickup_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Alış Zamanı'
    )
    pickup_kilometer = models.PositiveIntegerField(
        verbose_name='Alış Kilometresi'
    )
    dropoff_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Bırakış Zamanı'
    )
    dropoff_kilometer = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Bırakış Kilometresi'
    )
    destination = models.TextField(
        null=True,
        blank=True,
        verbose_name='Gidilen Yerler'
    )
    purpose = models.TextField(
        null=True,
        blank=True,
        verbose_name='İş Amacı'
    )
    reservation = models.ForeignKey(
        VehicleReservation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Rezervasyon'
    )
    
    class Meta:
        verbose_name = 'Araç Kullanımı'
        verbose_name_plural = 'Araç Kullanımları'
        ordering = ['-pickup_time']
    
    def __str__(self):
        status = "Aktif" if self.dropoff_time is None else "Tamamlandı"
        return f"{self.vehicle.plate} - {self.user.get_full_name()} ({status})"
    
    def clean(self):
        """Validate business rules"""
        errors = {}
        
        # If dropoff exists, validate kilometers
        if self.dropoff_time is not None:
            if self.dropoff_kilometer is None:
                errors['dropoff_kilometer'] = 'Bırakış kilometresi zorunludur.'
            elif self.pickup_kilometer and self.dropoff_kilometer < self.pickup_kilometer:
                errors['dropoff_kilometer'] = 'Bırakış kilometresi alış kilometresinden küçük olamaz.'
        
        # Check if vehicle is already in use (only if vehicle is set and this is a new pickup)
        if self.pk is None and self.dropoff_time is None and self.vehicle_id:
            try:
                existing = VehicleUsage.objects.filter(
                    vehicle_id=self.vehicle_id,
                    dropoff_time__isnull=True
                )
                if self.pk:
                    existing = existing.exclude(pk=self.pk)
                if existing.exists():
                    errors['__all__'] = 'Bu araç şu anda kullanımda.'
            except (AttributeError, ValueError):
                # Vehicle not set yet, skip this check
                pass
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def get_total_kilometers(self):
        """Calculate total kilometers for this usage"""
        if self.dropoff_kilometer and self.pickup_kilometer:
            return self.dropoff_kilometer - self.pickup_kilometer
        return None


class VehicleHistory(models.Model):
    """Admin-only metadata/history for a vehicle (not shown to normal users)."""

    COLOR_CHOICES = [
        ('Beyaz', 'Beyaz'),
        ('Siyah', 'Siyah'),
        ('Gri', 'Gri'),
        ('Gümüş', 'Gümüş'),
        ('Lacivert', 'Lacivert'),
        ('Mavi', 'Mavi'),
        ('Kırmızı', 'Kırmızı'),
        ('Bordo', 'Bordo'),
        ('Yeşil', 'Yeşil'),
        ('Sarı', 'Sarı'),
        ('Turuncu', 'Turuncu'),
        ('Kahverengi', 'Kahverengi'),
        ('Bej', 'Bej'),
    ]

    vehicle = models.OneToOneField(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name='Araç',
    )
    model_year = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Model Yılı',
    )
    color = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        choices=COLOR_CHOICES,
        verbose_name='Renk',
    )
    owner_person = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name='Araç Sahibi/Şahıs',
    )
    user_company_department = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name='Kullanıcı Şirket / Departman',
    )
    user_name = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name='Kullanıcı',
    )
    inspection_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Muayene Tarihi',
    )
    insurance_end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Sigorta Bitiş Tarihi',
    )
    casco_end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Kasko Bitiş Tarihi',
    )
    registration_document = models.FileField(
        upload_to='vehicle_documents/registration/',
        null=True,
        blank=True,
        verbose_name='Ruhsat Görseli',
    )
    insurance_casco_document = models.FileField(
        upload_to='vehicle_documents/insurance_casco/',
        null=True,
        blank=True,
        verbose_name='Sigorta/Kasko Görseli',
    )
    last_maintenance_kilometer = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='En Son Bakım Kilometresi',
    )
    last_user_notes = models.TextField(
        null=True,
        blank=True,
        verbose_name='Son Kullanıcı',
    )
    tire_size = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Lastik Ebatı',
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Güncelleme Zamanı',
    )

    class Meta:
        verbose_name = 'Araç Tarihçesi'
        verbose_name_plural = 'Araç Tarihçeleri'

    def __str__(self):
        return f"{self.vehicle.plate} - Tarihçe"

    @staticmethod
    def _remaining_days(target: date | None) -> int | None:
        if not target:
            return None
        today = timezone.localdate()
        return (target - today).days

    @property
    def inspection_remaining_days(self) -> int | None:
        return self._remaining_days(self.inspection_date)

    @property
    def insurance_remaining_days(self) -> int | None:
        return self._remaining_days(self.insurance_end_date)

    @property
    def casco_remaining_days(self) -> int | None:
        return self._remaining_days(self.casco_end_date)


class VehicleHistoryDocument(models.Model):
    """Documents attached to vehicle history records."""

    TYPE_REGISTRATION = 'REGISTRATION'
    TYPE_INSURANCE_CASCO = 'INSURANCE_CASCO'
    DOCUMENT_TYPE_CHOICES = [
        (TYPE_REGISTRATION, 'Ruhsat Görseli'),
        (TYPE_INSURANCE_CASCO, 'Sigorta/Kasko Görseli'),
    ]

    history = models.ForeignKey(
        VehicleHistory,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name='Araç Tarihçesi',
    )
    document_type = models.CharField(
        max_length=20,
        choices=DOCUMENT_TYPE_CHOICES,
        verbose_name='Belge Tipi',
    )
    file = models.FileField(
        upload_to='vehicle_documents/uploads/',
        verbose_name='Dosya',
    )
    original_filename = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Orijinal Dosya Adı',
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Yüklenme Zamanı',
    )

    class Meta:
        verbose_name = 'Araç Belgesi'
        verbose_name_plural = 'Araç Belgeleri'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.history.vehicle.plate} - {self.get_document_type_display()}"


class VehicleNote(models.Model):
    """Immutable notes attached to a vehicle."""

    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='notes',
        verbose_name='Araç',
    )
    note_text = models.TextField(
        verbose_name='Not',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Eklenme Zamanı',
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vehicle_notes',
        verbose_name='Ekleyen Kullanıcı',
    )

    class Meta:
        verbose_name = 'Araç Notu'
        verbose_name_plural = 'Araç Notları'
        ordering = ['created_at', 'id']

    def __str__(self):
        return f"{self.vehicle.plate} - Not {self.id}"

    def clean(self):
        text = (self.note_text or '').strip()
        if not text:
            raise ValidationError({'note_text': 'Boş not kaydedilemez.'})

    def save(self, *args, **kwargs):
        self.note_text = (self.note_text or '').strip()
        self.full_clean()
        super().save(*args, **kwargs)
