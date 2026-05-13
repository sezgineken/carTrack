"""
Management command to delete all data from the database.
Order: VehicleUsage -> VehicleReservation -> Vehicle -> User (FK constraints).
"""
from django.core.management.base import BaseCommand
from vehicles.models import VehicleUsage, VehicleReservation, Vehicle, User


class Command(BaseCommand):
    help = 'Veritabanındaki tüm verileri siler (User, Vehicle, VehicleReservation, VehicleUsage).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-input',
            action='store_true',
            help='Onay sormadan siler.',
        )

    def handle(self, *args, **options):
        if not options['no_input']:
            confirm = input('Tüm kullanıcılar, araçlar, rezervasyonlar ve kullanımlar silinecek. Devam? (evet/hayır): ')
            if confirm.strip().lower() != 'evet':
                self.stdout.write(self.style.WARNING('İşlem iptal edildi.'))
                return

        count_usage = VehicleUsage.objects.count()
        VehicleUsage.objects.all().delete()
        self.stdout.write(f'VehicleUsage: {count_usage} kayıt silindi.')

        count_res = VehicleReservation.objects.count()
        VehicleReservation.objects.all().delete()
        self.stdout.write(f'VehicleReservation: {count_res} kayıt silindi.')

        count_vehicle = Vehicle.objects.count()
        Vehicle.objects.all().delete()
        self.stdout.write(f'Vehicle: {count_vehicle} kayıt silindi.')

        count_user = User.objects.count()
        User.objects.all().delete()
        self.stdout.write(f'User: {count_user} kayıt silindi.')

        self.stdout.write(self.style.SUCCESS('Tüm veriler silindi. Superuser ve araçları kendiniz ekleyebilirsiniz.'))
