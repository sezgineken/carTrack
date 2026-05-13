from django.contrib import admin
from django.urls import path
from django.utils import timezone
from django.utils.html import format_html
from django.db.models import F

from .models import VehicleReservation, VehicleUsage
from .reservation_export import build_reservations_excel_response


class VehicleUsageInline(admin.TabularInline):
    model = VehicleUsage
    fk_name = 'reservation'
    extra = 0
    can_delete = False
    fields = (
        'vehicle',
        'user',
        'pickup_time',
        'pickup_kilometer',
        'dropoff_time',
        'dropoff_kilometer',
        'destination',
        'purpose',
    )
    readonly_fields = fields
    show_change_link = False

    def has_add_permission(self, request, obj=None):
        return False


class VehicleReservationAdmin(admin.ModelAdmin):
    """Vehicle Reservation Admin"""

    change_list_template = 'admin/vehicles/vehiclereservation/change_list.html'
    list_display = [
        'vehicle',
        'user_full_name_display',
        'start_time_display',
        'effective_end_time_display',
        'purpose_preview_display',
        'pickup_kilometer_display',
        'dropoff_kilometer_display',
        'handover_form_display',
    ]
    list_filter = ['start_time', 'is_active', 'vehicle', 'user']
    search_fields = ['vehicle__plate', 'user__username', 'user__first_name', 'user__last_name']
    date_hierarchy = 'start_time'
    ordering = ('-start_time', '-end_time', '-id')
    inlines = [VehicleUsageInline]
    fieldsets = (
        ('Temel Bilgiler', {'fields': ('vehicle', 'user', 'is_active')}),
        ('Zaman Bilgileri', {'fields': ('start_time', 'end_time')}),
        ('Diğer', {'fields': ('purpose', 'created_at')}),
    )
    readonly_fields = ['created_at']

    @staticmethod
    def _close_active_usages_for_reservations(reservations):
        now = timezone.now()
        reservation_ids = list(reservations.values_list('id', flat=True))
        if not reservation_ids:
            return
        VehicleUsage.objects.filter(
            reservation_id__in=reservation_ids,
            dropoff_time__isnull=True,
        ).update(
            dropoff_time=now,
            dropoff_kilometer=F('pickup_kilometer'),
        )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'export/',
                self.admin_site.admin_view(self.export_reservations_excel_view),
                name='vehicles_vehiclereservation_export',
            ),
        ]
        return custom_urls + urls

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('vehicle', 'user').prefetch_related('vehicleusage_set')

    def delete_model(self, request, obj):
        self._close_active_usages_for_reservations(
            VehicleReservation.objects.filter(pk=obj.pk)
        )
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset):
        self._close_active_usages_for_reservations(queryset)
        super().delete_queryset(request, queryset)

    @staticmethod
    def _related_usage(obj):
        if hasattr(obj, '_prefetched_objects_cache') and 'vehicleusage_set' in obj._prefetched_objects_cache:
            usages = obj._prefetched_objects_cache['vehicleusage_set']
            return usages[0] if usages else None
        return obj.vehicleusage_set.order_by('-pickup_time').first()

    def status_display(self, obj):
        if obj.is_current():
            return "🟢 Aktif"
        if obj.is_upcoming():
            return "📅 Yaklaşan"
        return "✅ Geçmiş"

    status_display.short_description = 'Durum'

    def user_full_name_display(self, obj):
        full_name = (obj.user.get_full_name() or '').strip()
        return full_name or obj.user.username

    user_full_name_display.short_description = 'KULLANICI'

    @staticmethod
    def _format_datetime_multiline(dt):
        local_dt = timezone.localtime(dt)
        return format_html(
            '<span style="display:inline-block;line-height:1.2;">{}<br>{}</span>',
            local_dt.strftime('%d.%m.%Y'),
            local_dt.strftime('%H:%M'),
        )

    def start_time_display(self, obj):
        if not obj.start_time:
            return '-'
        return self._format_datetime_multiline(obj.start_time)

    start_time_display.short_description = 'Başlangıç Zamanı'

    def effective_end_time_display(self, obj):
        usage = self._related_usage(obj)
        now = timezone.now()
        if usage and usage.dropoff_time:
            dt = usage.dropoff_time
        elif obj.end_time and obj.end_time <= now:
            dt = obj.end_time
        else:
            return '-'
        return self._format_datetime_multiline(dt)

    effective_end_time_display.short_description = 'Bitiş Zamanı'

    def purpose_preview_display(self, obj):
        purpose = (obj.purpose or '').strip()
        if not purpose:
            return '-'
        words = purpose.split()
        preview = purpose if len(words) <= 2 else f"{' '.join(words[:2])}..."
        return format_html(
            '<button type="button" class="purpose-preview-trigger" data-purpose="{}" '
            'style="border:0;background:none;padding:0;color:#001489;text-decoration:underline;cursor:pointer;display:inline-block;max-width:100%;white-space:nowrap;text-align:left;">'
            '{}</button>',
            purpose,
            preview,
        )

    purpose_preview_display.short_description = 'Amaç'

    def usage_status_display(self, obj):
        usage = self._related_usage(obj)
        if not usage:
            return "-"
        if usage.dropoff_time is None:
            return "🚗 Başladı"
        return "✅ Tamamlandı"

    usage_status_display.short_description = 'Kullanım'

    def pickup_kilometer_display(self, obj):
        usage = self._related_usage(obj)
        if not usage or usage.pickup_kilometer is None:
            return "-"
        return usage.pickup_kilometer

    pickup_kilometer_display.short_description = 'Alış KM'

    def dropoff_kilometer_display(self, obj):
        usage = self._related_usage(obj)
        if not usage or usage.dropoff_kilometer is None:
            return "-"
        return usage.dropoff_kilometer

    dropoff_kilometer_display.short_description = 'Bırakış KM'

    def handover_form_display(self, obj):
        usage = self._related_usage(obj)
        if not usage:
            return "-"
        return "Bekleniyor" if usage.dropoff_time is None else "Teslim Edildi"

    handover_form_display.short_description = 'Teslim Formu'

    def export_reservations_excel_view(self, request):
        changelist = self.get_changelist_instance(request)
        reservations = changelist.get_queryset(request).select_related('vehicle', 'user').prefetch_related('vehicleusage_set')
        rows = []
        for reservation in reservations:
            usage = self._related_usage(reservation)
            planned_end = timezone.localtime(reservation.end_time).strftime('%d.%m.%Y %H:%M') if reservation.end_time else ''
            effective_end = timezone.localtime(usage.dropoff_time).strftime('%d.%m.%Y %H:%M') if usage and usage.dropoff_time else planned_end
            rows.append([
                str(reservation.vehicle),
                str(reservation.user),
                timezone.localtime(reservation.start_time).strftime('%d.%m.%Y %H:%M') if reservation.start_time else '',
                effective_end,
                reservation.purpose or '',
                'Evet' if reservation.is_active else 'Hayır',
                self.status_display(reservation),
                self.usage_status_display(reservation),
                self.pickup_kilometer_display(reservation),
                self.dropoff_kilometer_display(reservation),
                self.handover_form_display(reservation),
                timezone.localtime(reservation.created_at).strftime('%d.%m.%Y %H:%M') if reservation.created_at else '',
            ])
        return build_reservations_excel_response(rows)
