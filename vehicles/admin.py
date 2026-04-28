from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.admin.sites import NotRegistered

from .admin_reservation import VehicleReservationAdmin
from .admin_usage import VehicleUsageAdmin
from .admin_user import UserAdmin
from .admin_vehicle import VehicleAdmin
from .models import User, Vehicle, VehicleReservation, VehicleUsage

# Customize admin site
admin.site.site_header = 'Araç Takip Yönetim Sistemi'
admin.site.site_title = 'Araç Takip Yönetim Sistemi'
admin.site.index_title = 'Araç Takip Yönetim Sistemi'

admin.site.register(User, UserAdmin)
admin.site.register(Vehicle, VehicleAdmin)
admin.site.register(VehicleUsage, VehicleUsageAdmin)
admin.site.register(VehicleReservation, VehicleReservationAdmin)

try:
    admin.site.unregister(Group)
except NotRegistered:
    pass
