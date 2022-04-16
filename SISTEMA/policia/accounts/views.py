from django.shortcuts import render
from django.http import HttpResponse

def home(request):
    return render(request,'accounts/dashboard.html')

def registro(request):
    return render(request,'accounts/registro.html')

def consulta(request):
    return render(request,'accounts/consulta.html')
