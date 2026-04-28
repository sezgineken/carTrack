from django.contrib import admin, messages
from django.utils import timezone

from .models import VehicleReservation, VehicleUsage


class VehicleUsageAdmin(admin.ModelAdmin):
    """Vehicle Usage Admin"""

    list_display = [
        'vehicle',
        'user',
        'pickup_time',
        'pickup_kilometer',
        'dropoff_time',
        'dropoff_kilometer',
        'status_display',
    ]
    list_filter = ['pickup_time', 'vehicle', 'user']
    search_fields = ['vehicle__plate', 'user__username', 'user__first_name', 'user__last_name']
    readonly_fields = ['pickup_time']
    date_hierarchy = 'pickup_time'
    actions = ['cancel_active_usages']

    fieldsets = (
        ('Temel Bilgiler', {'fields': ('vehicle', 'user', 'pickup_time')}),
        ('Alış Bilgileri', {'fields': ('pickup_kilometer',)}),
        ('Bırakış Bilgileri', {'fields': ('dropoff_time', 'dropoff_kilometer', 'destination', 'purpose')}),
    )

    def status_display(self, obj):
        if obj.dropoff_time is None:
            return "🟢 Aktif"
        return "✅ Tamamlandı"

    status_display.short_description = 'Durum'

    @admin.action(description='Seçilen aktif kullanımları iptal et (sil)')
    def cancel_active_usages(self, request, queryset):
        active_qs = queryset.filter(dropoff_time__isnull=True)
        active_count = active_qs.count()
        if active_count == 0:
            self.message_user(request, 'Seçilen kayıtlarda aktif kullanım yok.', level=messages.WARNING)
            return

        now = timezone.now()
        reservation_ids = list(active_qs.exclude(reservation_id__isnull=True).values_list('reservation_id', flat=True))
        if reservation_ids:
            VehicleReservation.objects.filter(id__in=reservation_ids).update(is_active=False, end_time=now)
        deleted_count, _ = active_qs.delete()
        self.message_user(
            request,
            f'{deleted_count} aktif kullanım iptal edildi. İlişkili rezervasyonlar pasife alındı.',
        )

    # Keep model registered for links/internals, but hide from admin menu.
    def has_module_permission(self, request):
        return False

    def get_model_perms(self, request):
        return {}
