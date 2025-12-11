from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from .data.users import User as DataUser
from .data.message import Message, Complaint, Compliment, Thread


def _require_post(request, fallback='index'):
    """Small helper to enforce POST-only views."""
    if request.method != 'POST':
        return redirect(fallback)
    return None


def _require_login(request):
    """Ensure the user is authenticated before submitting feedback."""
    if not request.user.is_authenticated:
        messages.error(request, 'Please log in to submit feedback.')
        return redirect('login')
    return None


def submit_complaint(request):
    # Enforce POST and authentication
    resp = _require_post(request)
    if resp:
        return resp
    resp = _require_login(request)
    if resp:
        return resp

    filed_against = request.POST.get('filed_against')
    description = request.POST.get('description', '').strip()

    if not filed_against or not description:
        messages.error(request, 'Missing target or description for complaint.')
        return redirect('index')

    try:
        target_id = int(filed_against)
    except (TypeError, ValueError):
        messages.error(request, 'Invalid complaint target.')
        return redirect('index')

    target = get_object_or_404(DataUser, pk=target_id)
    sender = request.user

    # Create a lightweight thread to satisfy the non-null Message.thread
    thread_title = f"Complaint from {sender.username} about {target.username}"
    t = Thread.objects.create(title=thread_title[:100], creation_date=timezone.now())

    msg = Message.objects.create(thread=t, message=description, who=sender, when=timezone.now())
    Complaint.objects.create(sender=sender, to=target, message=msg)
    messages.success(request, 'Complaint submitted.')
    return redirect('profile', user_id=target.id)


def submit_compliment(request):
    # Enforce POST and authentication
    resp = _require_post(request)
    if resp:
        return resp
    resp = _require_login(request)
    if resp:
        return resp

    filed_against = request.POST.get('filed_against')
    description = request.POST.get('description', '').strip()

    if not filed_against or not description:
        messages.error(request, 'Missing target or message for compliment.')
        return redirect('index')

    try:
        target_id = int(filed_against)
    except (TypeError, ValueError):
        messages.error(request, 'Invalid compliment target.')
        return redirect('index')

    target = get_object_or_404(DataUser, pk=target_id)
    sender = request.user

    thread_title = f"Compliment from {sender.username} to {target.username}"
    t = Thread.objects.create(title=thread_title[:100], creation_date=timezone.now())

    msg = Message.objects.create(thread=t, message=description, who=sender, when=timezone.now())
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
