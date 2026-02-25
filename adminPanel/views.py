from django.shortcuts import render

# Create your views here.

def adminPanel(request):
    return render(request , 'adminPanel/admin.html')
