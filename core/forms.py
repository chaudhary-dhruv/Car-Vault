from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User

class UserSignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['email' , 'role' ,'password1', 'password2']

        widgets = {
            'password1' :forms.PasswordInput(),
            'password2' :forms.PasswordInput(),
        }
