from django.urls import path, reverse_lazy
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('vehicles/', views.vehicle_list_view, name='vehicle_list'),
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('password-change/', auth_views.PasswordChangeView.as_view(
        template_name='vehicles/password_change.html',
        success_url=reverse_lazy('password_change_done')
    ), name='password_change'),
    path('password-change-done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='vehicles/password_change_done.html'
    ), name='password_change_done'),
    path('vehicle/<int:vehicle_id>/reservation/create/', views.vehicle_reservation_create_view, name='vehicle_reservation_create'),
    path(
        'vehicle/<int:vehicle_id>/reservation/availability/',
        views.reservation_availability_check_view,
        name='reservation_availability_check',
    ),
    path('reservation/<int:reservation_id>/contract-complete/', views.vehicle_reservation_contract_complete_view, name='vehicle_reservation_contract_complete'),
    path('reservation/<int:reservation_id>/contract-download/', views.vehicle_reservation_contract_download_view, name='vehicle_reservation_contract_download'),
    path('vehicle/<int:vehicle_id>/reservations/', views.vehicle_reservation_list_view, name='vehicle_reservation_list'),
    path('reservation/<int:reservation_id>/cancel/', views.vehicle_reservation_cancel_view, name='vehicle_reservation_cancel'),
    path('reservation/<int:reservation_id>/finish/', views.vehicle_reservation_finish_view, name='vehicle_reservation_finish'),
    path('reservation/<int:reservation_id>/extend/', views.vehicle_reservation_extend_view, name='vehicle_reservation_extend'),
    path('vehicle/usage/complete/', views.vehicle_usage_complete_view, name='vehicle_usage_complete'),
    path('vehicle/usage/pending-status/', views.pending_usage_status_view, name='pending_usage_status'),
    path('vehicle/kilometer-status/', views.vehicle_kilometer_status_view, name='vehicle_kilometer_status'),
]

