from django.shortcuts import render

def home(request):
    return render(request, 'src/templates/index.html')
