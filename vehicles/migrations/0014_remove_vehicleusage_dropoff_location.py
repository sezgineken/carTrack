# Generated manually for removing unused dropoff_location field

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vehicles', '0013_alter_vehicle_location'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='vehicleusage',
            name='dropoff_location',
        ),
    ]
