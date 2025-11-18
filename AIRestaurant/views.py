from django.shortcuts import render
from django.http import JsonResponse
from subprocess import run as shell

def home(request):
    return render(request, 'index.html')

def add_to_cart(request):
    return render(request, 'cart.html')

def ai_chat(request, question):
    AI_PATH = "/home/SapphireBrick613/AI"
    result = shell(
        [f'{AI_PATH}/llama-run', f'{AI_PATH}/tinyllama-1.1b-chat-v1.0.Q4_0.gguf'],
        capture_output=True,
        input=question,
        encoding='utf-8')
    response = result.stdout if result.returncode == 0 else "<AI failed>"
    return JsonResponse({
        "answer": response,
        "rating_id": 0,
        "source": "AI",
    })