from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .decorators import role_required

# Create your views here.
@role_required(allowed_roles=["user"])
def home(request):
    return render(request , 'user/home.html')