"""
URL configuration for cartrack project.
Tüm uygulama URL'leri /cartrack/ prefix'i altında.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls.static import static

urlpatterns = [
    path('', RedirectView.as_view(url='/cartrack/', permanent=False)),
    path(
        'favicon.ico',
        RedirectView.as_view(
            url=f'{settings.STATIC_URL}favicon.ico',
            permanent=False,
        ),
    ),
    path('cartrack/admin/', admin.site.urls),
]
if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += [
    path('cartrack/', include('vehicles.urls')),
]

