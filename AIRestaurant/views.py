from django.shortcuts import render

def home(request):
    return render(request, 'index.html')

def add_to_cart(request):
    return render(request,'cart.html')