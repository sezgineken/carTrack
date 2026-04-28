"""
Management command to process active reservations and create vehicle usages
Run this command periodically (e.g., via cron) to automatically start reservations
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from vehicles.models import VehicleReservation, VehicleUsage, Vehicle


class Command(BaseCommand):
    help = 'Process active reservations and create vehicle usages when reservation time arrives'

    def handle(self, *args, **options):
        now = timezone.now()
        
        # Find reservations that should start now (within last 5 minutes to account for timing)
        active_reservations = VehicleReservation.objects.filter(
            is_active=True,
            start_time__lte=now,
            start_time__gte=now - timedelta(minutes=5)
        ).select_related('vehicle', 'user')
        
        created_count = 0
        skipped_count = 0
        
        for reservation in active_reservations:
            vehicle = reservation.vehicle
            
            # Check if vehicle is already in use
            if not vehicle.is_available():
                self.stdout.write(
                    self.style.WARNING(
                        f'Vehicle {vehicle.plate} is already in use, skipping reservation {reservation.id}'
                    )
                )
                skipped_count += 1
                continue

            if VehicleUsage.objects.filter(reservation=reservation).exists():
                skipped_count += 1
                continue
            
            # Get the last dropoff kilometer for this vehicle
            last_usage = VehicleUsage.objects.filter(
                vehicle=vehicle,
                dropoff_time__isnull=False
            ).order_by('-dropoff_time').first()
            
            pickup_kilometer = (
                last_usage.dropoff_kilometer
                if last_usage and last_usage.dropoff_kilometer is not None
                else vehicle.initial_kilometer
            )
            
            # Create vehicle usage from reservation
            usage = VehicleUsage.objects.create(
                vehicle=vehicle,
                user=reservation.user,
                pickup_kilometer=pickup_kilometer,
                purpose=reservation.purpose or f'Rezervasyon: {reservation.start_time}',
                reservation=reservation
            )
            
            created_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'Created usage {usage.id} for vehicle {vehicle.plate} from reservation {reservation.id}'
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Processed {active_reservations.count()} reservations: {created_count} created, {skipped_count} skipped'
            )
        )

