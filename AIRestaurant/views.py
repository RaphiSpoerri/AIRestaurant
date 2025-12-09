from django.shortcuts import render
from django.http import JsonResponse
from subprocess import run as shell
from urllib.parse import unquote
from django.shortcuts import get_object_or_404
from .models import User as DataUser, Customer, DishRating, Dish, Deliverer, Chef, Manager, Compliment, Complaint, Message
from django.db.models import Avg
from django.utils import timezone
from django.shortcuts import redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from .data.message import Thread

def home(request):
    return render(request, 'index.html')
def menu(request):
    return render(request, 'menu.html', {'dishes': Dish.objects.all().values()})
def add_to_cart(request):
    return render(request, 'cart.html')

def rate_dish(request, dish_id):
    return render(request, 'rate_dish.html', {'dish_id': dish_id})

def update_cart(request):
    return render(request, 'cart.html')
def cart(request):
    return render(request, 'cart.html')
def __getattr__(name):
    return lambda request, *args: render(request, f'{name}.html', *args)

def ai_chat(request):
    AI_PATH = "/home/SapphireBrick613/AI"
    question = unquote(request.POST.get('query'))
    result = shell(
        [f'{AI_PATH}/llama-run', f'{AI_PATH}/tinyllama-1.1b-chat-v1.0.Q4_0.gguf'],
        capture_output=True,
        input=question,
        encoding='utf-8')
    response = result.stdout.replace("\x1b[0m", "") if result.returncode == 0 else "<AI failed>"

    return JsonResponse({
        "answer": response,
        "rating_id": 0,
        "source": "AI",
    })


def profile_view(request, user_id):
    """Render combined dashboard + public profile for the given user id.

    Chooses template based on the target user's type: customer/chef/deliverer/manager.
    This view provides `target`, `profile`, `compliments`, `complaints`,
    `avg_dish_rating` (when relevant), and `can_view_private` in the context.
    """
    target = get_object_or_404(DataUser, pk=user_id)

    # viewer is the Django request.user (project templates already reference `user`)
    viewer = request.user

    # default context values
    context = {
        'target': target,
        'user': viewer,  # keep same variable name templates expect
        'viewer': viewer,
        'profile': None,
        'compliments': [],
        'complaints': [],
        'avg_dish_rating': None,
        'can_view_private': False,
    }

    # load profile model instance if present
    if target.type == 'CU':
        context['profile'] = Customer.objects.filter(login=target).first()
    elif target.type == 'CH':
        context['profile'] = Chef.objects.filter(login=target).first()
    elif target.type == 'DL':
        context['profile'] = Deliverer.objects.filter(login=target).first()
    elif target.type == 'MN':
        context['profile'] = Manager.objects.filter(login=target).first()

    # compliments and complaints (show latest first)
    context['compliments'] = list(Compliment.objects.filter(to=target).select_related('sender', 'message').order_by('-id')[:50])
    context['complaints'] = list(Complaint.objects.filter(to=target).select_related('sender', 'message').order_by('-id')[:50])

    # compute average dish rating for chefs
    if target.type == 'CH':
        try:
            avg = DishRating.objects.filter(dish__chef__login=target).aggregate(avg=Avg('rating'))['avg']
            if avg is not None:
                context['avg_dish_rating'] = round(avg, 2)
        except Exception:
            context['avg_dish_rating'] = None

    # Compute permission grouping (three categories): public / relevant / private
    viewer_type = getattr(viewer, 'type', None)
    is_manager_viewer = getattr(viewer, 'is_staff', False) or getattr(viewer, 'is_superuser', False) or (viewer_type == 'MN')
    is_owner = getattr(viewer, 'id', None) == getattr(target, 'id', None)

    # public_visible: fields shown to everyone (templates can assume this)
    context['public_visible'] = True
    # relevant_visible: data shown to viewers who can affect reputation, or managers
    context['relevant_visible'] = is_manager_viewer or (viewer_type in ('CU', 'DL', 'CH'))
    # private_visible: private fields shown to owner and managers
    context['private_visible'] = is_owner or is_manager_viewer

    # pick template by target type
    tpl_map = {'CU': 'customer.html', 'CH': 'chef.html', 'DL': 'deliverer.html', 'MN': 'manager.html'}
    tpl = tpl_map.get(target.type, 'customer.html')

    return render(request, tpl, context)


def discussions(request):
    """List recent threads and support searching by title via GET param `q`."""
    q = request.GET.get('q', '').strip()
    if q:
        threads = list(Thread.objects.filter(title__icontains=q).order_by('-creation_date')[:50])
    else:
        threads = list(Thread.objects.all().order_by('-creation_date')[:10])

    return render(request, 'discussions.html', {
        'threads': threads,
        'query': q,
    })


@require_POST
def create_thread(request):
    """Create a new thread with the given `title` POST parameter and redirect to it.

    Also creates an initial Message marking the creator and creation time so the
    thread has a visible starter.
    """
    title = request.POST.get('title', '').strip()
    if not title:
        messages.error(request, 'Thread title cannot be empty.')
        return redirect('discussions')

    t = Thread.objects.create(title=title, creation_date=timezone.now())
    # create an initial message indicating the thread was created
    Message.objects.create(thread=t, message='Thread created', who=request.user, when=timezone.now())
    return redirect('thread', thread_id=t.id)


def thread_view(request, thread_id):
    t = get_object_or_404(Thread, pk=thread_id)
    messages_qs = Message.objects.filter(thread=t).select_related('who').order_by('when')

    # determine starter (earliest message author)
    starter = None
    starter_date = None
    first_msg = messages_qs.first()
    if first_msg:
        starter = first_msg.who
        starter_date = first_msg.when

    return render(request, 'thread.html', {
        'thread': t,
        'starter': starter,
        'starter_date': starter_date,
        'messages': messages_qs,
    })


def random_deliverer(request):
    """Return a JSON object with a random deliverer (name, id).

    This is a lightweight helper used by the `place_order.html` client-side
    countdown to show a deliverer once one has been assigned.
    """
    d = Deliverer.objects.order_by('?').first()
    if not d:
        return JsonResponse({'error': 'no_deliverers'}, status=404)

    # d.login should be the User model instance representing the deliverer
    login = getattr(d, 'login', None)
    name = getattr(login, 'name', '') if login else ''
    return JsonResponse({'id': getattr(login, 'id', None), 'name': name})