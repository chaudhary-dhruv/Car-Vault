from django.shortcuts import render , redirect
from .forms import UserSignupForm
from .models import User

# Create your views here.

def userSignupView(request):
    if request.method == "POST":
        form = UserSignupForm(request.POST or None)
        if form.is_valid():
            form.save()
            return redirect('login')  # it throw error bcz login was not exist now
        else:
            return render(request , 'core/SignUp.html' , {'form' : form})
    else:
        form = UserSignupForm()
        return render(request , 'core/SignUp.html' , {'form' : form})


