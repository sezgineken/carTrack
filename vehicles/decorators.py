from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def manager_required(view_func):
    """Decorator to require manager role"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_manager():
            messages.error(request, 'Bu sayfaya erişim yetkiniz yok.')
            return redirect('vehicle_list')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

