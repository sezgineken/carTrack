from django.db import migrations, models


def repair_reservation_flag_columns(apps, schema_editor):
    VehicleReservation = apps.get_model("vehicles", "VehicleReservation")
    table_name = VehicleReservation._meta.db_table

    with schema_editor.connection.cursor() as cursor:
        existing_columns = {
            column.name
            for column in schema_editor.connection.introspection.get_table_description(
                cursor, table_name
            )
        }

    if "is_late_return" not in existing_columns:
        late_field = models.BooleanField(default=False, verbose_name="Gecikmeli Dönüş")
        late_field.set_attributes_from_name("is_late_return")
        schema_editor.add_field(VehicleReservation, late_field)

    if "is_no_show" not in existing_columns:
        no_show_field = models.BooleanField(default=False, verbose_name="Gelmedi")
        no_show_field.set_attributes_from_name("is_no_show")
        schema_editor.add_field(VehicleReservation, no_show_field)


class Migration(migrations.Migration):
    dependencies = [
        ("vehicles", "0019_sync_reservation_flags"),
    ]

    operations = [
        migrations.RunPython(repair_reservation_flag_columns, migrations.RunPython.noop),
    ]

