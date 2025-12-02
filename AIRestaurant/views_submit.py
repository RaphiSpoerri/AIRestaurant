from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from .data.users import User as DataUser
from .data.message import Message, Complaint, Compliment
from .data.message import Thread


def submit_complaint(request):
    if request.method != 'POST':
        return redirect('index')

    filed_against = request.POST.get('filed_against')
    description = request.POST.get('description', '').strip()
    ctype = request.POST.get('type', 'other')

    if not filed_against or not description:
        messages.error(request, 'Missing target or description for complaint.')
        return redirect('index')

    target = get_object_or_404(DataUser, pk=int(filed_against))
    sender = request.user

    # create message and complaint
    msg = Message.objects.create(thread=None, message=description, who=sender, when=timezone.now())
    Complaint.objects.create(sender=sender, to=target, message=msg)
    messages.success(request, 'Complaint submitted.')
    return redirect('profile', user_id=target.id)


def submit_compliment(request):
    if request.method != 'POST':
        return redirect('index')

    filed_against = request.POST.get('filed_against')
    description = request.POST.get('description', '').strip()
    ctype = request.POST.get('type', 'other')

    if not filed_against or not description:
        messages.error(request, 'Missing target or message for compliment.')
        return redirect('index')

    target = get_object_or_404(DataUser, pk=int(filed_against))
    sender = request.user

    msg = Message.objects.create(thread=None, message=description, who=sender, when=timezone.now())
    Compliment.objects.create(sender=sender, to=target, message=msg)
    messages.success(request, 'Compliment submitted.')
    return redirect('profile', user_id=target.id)


def submit_message(request):
    if request.method != 'POST':
        return redirect('discussions')

    thread_id = request.POST.get('thread_id')
    text = request.POST.get('message', '').strip()
    if not thread_id or not text:
        messages.error(request, 'Missing thread or message text.')
        return redirect('discussions')

    try:
        t = Thread.objects.get(pk=int(thread_id))
    except Exception:
        messages.error(request, 'Thread not found.')
        return redirect('discussions')

    Message.objects.create(thread=t, message=text, who=request.user, when=timezone.now())
    return redirect('thread', thread_id=t.id)
