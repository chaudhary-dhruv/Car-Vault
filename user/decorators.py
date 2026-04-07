from functools import wraps

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect

from core.models import User


def role_required(allowed_roles=None):
    allowed_roles = allowed_roles or []

    def decorator(view_func):
        @wraps(view_func)
        def wrapper_func(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")
            if request.user.account_state != User.AccountState.ACTIVE:
                messages.error(request, "Your account is not active yet.")
                return redirect("login")
            if request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            return HttpResponse("You are not authorized to view this page.")

        return wrapper_func

    return decorator
