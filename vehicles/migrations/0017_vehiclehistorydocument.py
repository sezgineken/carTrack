from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vehicles', '0016_vehiclehistory_documents'),
    ]

    operations = [
        migrations.CreateModel(
            name='VehicleHistoryDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('document_type', models.CharField(choices=[('REGISTRATION', 'Ruhsat Görseli'), ('INSURANCE_CASCO', 'Sigorta/Kasko Görseli')], max_length=20, verbose_name='Belge Tipi')),
                ('file', models.FileField(upload_to='vehicle_documents/uploads/', verbose_name='Dosya')),
                ('original_filename', models.CharField(blank=True, max_length=255, verbose_name='Orijinal Dosya Adı')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True, verbose_name='Yüklenme Zamanı')),
                ('history', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='documents', to='vehicles.vehiclehistory', verbose_name='Araç Tarihçesi')),
            ],
            options={
                'verbose_name': 'Araç Belgesi',
                'verbose_name_plural': 'Araç Belgeleri',
                'ordering': ['-uploaded_at'],
            },
        ),
    ]
