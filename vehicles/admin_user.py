from django.contrib.auth.admin import UserAdmin as BaseUserAdmin


class UserAdmin(BaseUserAdmin):
    """Custom User Admin"""

    list_display = ['username', 'email', 'first_name', 'last_name', 'duty', 'role', 'is_active']
    list_filter = ['role', 'is_active', 'is_staff']
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Kişisel Bilgiler', {'fields': ('first_name', 'last_name', 'duty', 'email')}),
        ('Ek Bilgiler', {'fields': ('role',)}),
        ('Yetkiler', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Önemli Tarihler', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Kişisel Bilgiler', {'fields': ('first_name', 'last_name', 'duty', 'email')}),
        ('Ek Bilgiler', {'fields': ('role',)}),
    )
