from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [

    path('signUp/' , views.userSignupView, name='signUp'),
    path('temp/' , views.tempFile),    
    path('login/' , views.userLoginView , name='login')
]