from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('vehicles', '0017_vehiclehistorydocument'),
    ]

    operations = [
        migrations.CreateModel(
            name='VehicleNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('note_text', models.TextField(verbose_name='Not')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Eklenme Zamanı')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='vehicle_notes', to=settings.AUTH_USER_MODEL, verbose_name='Ekleyen Kullanıcı')),
                ('vehicle', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notes', to='vehicles.vehicle', verbose_name='Araç')),
            ],
            options={
                'verbose_name': 'Araç Notu',
                'verbose_name_plural': 'Araç Notları',
                'ordering': ['created_at', 'id'],
            },
        ),
    ]
