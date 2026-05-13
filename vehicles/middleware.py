from django.shortcuts import redirect
from django.urls import reverse

from .views import get_pending_usage_for_user, start_due_reservations


class ForceVehicleUsageCompletionMiddleware:
    """Redirect users to usage completion page until mandatory fields are filled."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            start_due_reservations()
            pending_usage = get_pending_usage_for_user(user)
            if pending_usage:
                allowed_paths = {
                    reverse('vehicle_usage_complete'),
                    reverse('pending_usage_status'),
                    reverse('logout'),
                }
                if request.path not in allowed_paths:
                    return redirect('vehicle_usage_complete')

        return self.get_response(request)
