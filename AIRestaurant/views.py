from django.shortcuts import render
from django.http import JsonResponse
from subprocess import run as shell

def home(request):
    return render(request, 'index.html')

def add_to_cart(request):
    return render(request, 'cart.html')

def ai_chat(request):
    if request.POST:
        question = request.POST.get("query")
        AI_PATH = "/home/SapphireBrick613/AI"
        result = shell(
            [f'{AI_PATH}/llama-run', f'{AI_PATH}/tinyllama-1.1b-chat-v1.0.Q4_0.gguf'],
            capture_output=True,
            input=question,
            encoding=True)
        response = result.stdout if result.returncode == 0 else "<AI failed>"
        return JsonResponse({
            "answer": response,
            "rating_id": 0,
            "source": "AI",
        })
    else:
        return render(request, "ai_chat.html")