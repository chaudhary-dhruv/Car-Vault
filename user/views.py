from django.shortcuts import redirect
from .decorators import role_required

# Create your views here.
@role_required(allowed_roles=["buyer"])
def home(request):
    return redirect("buyer_dashboard")
