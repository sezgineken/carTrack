from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vehicles', '0015_vehicle_ownership'),
    ]

    operations = [
        migrations.AddField(
            model_name='vehiclehistory',
            name='insurance_casco_document',
            field=models.FileField(
                blank=True,
                null=True,
                upload_to='vehicle_documents/insurance_casco/',
                verbose_name='Sigorta/Kasko Görseli',
            ),
        ),
        migrations.AddField(
            model_name='vehiclehistory',
            name='registration_document',
            field=models.FileField(
                blank=True,
                null=True,
                upload_to='vehicle_documents/registration/',
                verbose_name='Ruhsat Görseli',
            ),
        ),
    ]
