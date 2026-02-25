from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('signUp/' , views.userSignupView, name='signUp'),
    path('temp/' , views.tempFile),
    path('adminPanel/' , views.adminPanel),
    path('login/' , views.userLoginView , name='login')
]