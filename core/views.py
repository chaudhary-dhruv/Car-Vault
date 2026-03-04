from django.shortcuts import render , redirect
from django.contrib.auth import authenticate,login
from .forms import UserSignupForm , UserLoginForm
from .models import User
from django.conf import settings
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
import os


# Create your views here.

def userSignupView(request):
    if request.method == "POST":
        form = UserSignupForm(request.POST)

        if form.is_valid():
            # Save user first
            user = form.save()

            # Send email AFTER successful save
            send_welcome_email(user)

            return redirect('login')

        return render(request, 'core/SignUp.html', {'form': form})

    else:
        form = UserSignupForm()
        return render(request, 'core/SignUp.html', {'form': form})

def send_welcome_email(user):

    subject = "Welcome to Car Vault 🚗"
    from_email = settings.EMAIL_HOST_USER
    to_email = [user.email]

    # Render HTML template
    html_content = render_to_string(
        "email/welcome_email.html",
        {"user": user}
    )

    # Plain text fallback
    text_content = f'''
    Hi {user.firstname},

    Thank you for registering with Car Vault.
    Start comparing cars today!
    '''

    email = EmailMultiAlternatives(
        subject,
        text_content,
        from_email,
        to_email
    )

    # Attach HTML version
    email.attach_alternative(html_content, "text/html")

    # Optional: Attach PDF file
    file_path = os.path.join(settings.BASE_DIR, "static", "files", "welcome_file.pdf")

    if os.path.exists(file_path):
        email.attach_file(file_path)

    email.send()


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

 

def TryHTML(request):
    return render(request , "core/try_html.html")