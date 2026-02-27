from django.shortcuts import render , redirect
from django.contrib.auth import authenticate,login
from .forms import UserSignupForm , UserLoginForm
from .models import User
from django.conf import settings
from django.core.mail import send_mail

# Create your views here.

def userSignupView(request):
    if request.method == "POST":
        form = UserSignupForm(request.POST or None)
        if form.is_valid():
            email = form.cleaned_data['email']
            send_mail(
                subject="Welcome to Car Vault",
                message="Thank you for registering with car vault",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email]
            )
            
            form.save()
            return redirect('login') 
        else:
            return render(request , 'core/SignUp.html' , {'form' : form})
    else:
        form = UserSignupForm()
        return render(request , 'core/SignUp.html' , {'form' : form})
    

def userLoginView(request):
    if request.method == "POST":
        form = UserLoginForm(request.POST or None)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request , email=email , password=password)
            if user:
                login(request , user)
                if user.role == "user":
                    return redirect("user_dashboard")
                elif user.role == "admin":
                    return redirect("admin_dashboard")
            else:
                return render(request , "core/login.html" , {'form' : form})

    else:
        form  = UserLoginForm()
        return render(request , "core/login.html" , {'form' : form})

def tempFile(request):
    return render(request , "core/temp.html")

 

