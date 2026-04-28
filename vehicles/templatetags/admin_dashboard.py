from datetime import timedelta

from django import template
from django.utils import timezone

from vehicles.models import Vehicle, VehicleHistory, VehicleReservation, VehicleUsage

register = template.Library()


@register.simple_tag
def get_dashboard_metrics():
    now = timezone.now()
    today = timezone.localdate()
    next_24h = now + timedelta(hours=24)

    active_usages = VehicleUsage.objects.filter(dropoff_time__isnull=True).count()
    pending_handover = VehicleUsage.objects.filter(
        dropoff_time__isnull=True,
        reservation__isnull=False,
        reservation__is_active=True,
        reservation__end_time__lte=now,
    ).count()
    starting_today = VehicleReservation.objects.filter(
        is_active=True,
        start_time__date=today,
    ).count()
    ending_next_24h = VehicleReservation.objects.filter(
        is_active=True,
        end_time__gte=now,
        end_time__lte=next_24h,
    ).count()

    total_vehicle_count = Vehicle.objects.count()
    visible_vehicle_ids = set(
        Vehicle.objects.filter(is_active=True, show_in_pool=True).values_list('id', flat=True)
    )
    pool_total_count = len(visible_vehicle_ids)

    visible_out_of_service_vehicle_ids = set(
        Vehicle.objects.filter(
            is_active=True,
            show_in_pool=True,
            operational_status='PASSIVE',
        ).values_list('id', flat=True)
    )
    pool_active_out_of_service_count = len(visible_out_of_service_vehicle_ids)

    in_use_vehicle_ids = set(
        VehicleUsage.objects.filter(
            vehicle_id__in=visible_vehicle_ids,
            dropoff_time__isnull=True,
        ).values_list('vehicle_id', flat=True)
    )
    reserved_now_vehicle_ids = set(
        VehicleReservation.objects.filter(
            is_active=True,
            vehicle_id__in=visible_vehicle_ids,
            start_time__lte=now,
            end_time__gte=now,
        ).values_list('vehicle_id', flat=True)
    )

    # Keep pie slices mutually exclusive so chart matches legend totals.
    usage_or_reserved_vehicle_ids = (
        (in_use_vehicle_ids | reserved_now_vehicle_ids) - visible_out_of_service_vehicle_ids
    )
    available_vehicle_ids = (
        visible_vehicle_ids - visible_out_of_service_vehicle_ids - usage_or_reserved_vehicle_ids
    )

    return {
        'active_usages': active_usages,
        'pending_handover': pending_handover,
        'starting_today': starting_today,
        'ending_next_24h': ending_next_24h,
        'pie': {
            'total': total_vehicle_count,
            'pool_total': pool_total_count,
            'pool_out_of_service': pool_active_out_of_service_count,
            'in_use': len(usage_or_reserved_vehicle_ids),
            'reserved': 0,
            'available': len(available_vehicle_ids),
        },
    }


@register.simple_tag
def get_risk_vehicles(critical_days=30):
    today = timezone.localdate()
    items = []
    histories = VehicleHistory.objects.select_related('vehicle').all()

    def append_if_risky(history, date_value, label):
        if not date_value:
            return
        remaining = (date_value - today).days
        if remaining <= critical_days:
            items.append(
                {
                    'plate': history.vehicle.plate,
                    'brand_model': history.vehicle.brand_model,
                    'type_label': label,
                    'target_date': date_value,
                    'remaining_days': remaining,
                }
            )

    for history in histories:
        append_if_risky(history, history.inspection_date, 'Muayene')
        append_if_risky(history, history.insurance_end_date, 'Sigorta')
        append_if_risky(history, history.casco_end_date, 'Kasko')

    items.sort(key=lambda item: item['remaining_days'])
    return items[:20]
