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
from django.db import IntegrityError
from django.views.decorators.http import require_POST
from .data.message import Thread
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.urls import reverse
def home(request):
    return render(request, 'index.html', {'user': request.user})
def menu(request):
    return render(request, 'menu.html', {'dishes': Dish.objects.all().values()})
def add_to_cart(request):
    return render(request, 'cart.html')

def rate_dish(request, dish_id):
    return render(request, 'rate_dish.html', {'dish_id': dish_id})


def rate_ai_response(request, rating_id):
    """Stub: record a rating for an AI response and return JSON."""
    if request.method == 'POST':
        # placeholder: in real app, save rating to DB
        return JsonResponse({'status': 'ok', 'rating_id': rating_id})
    return JsonResponse({'error': 'POST required'}, status=400)


def remove_from_cart(request, menu_id):
    # placeholder: remove item from session/cart then redirect
    return redirect('cart')


def place_order(request):
    # placeholder: show place order page or handle POST to create order
    if request.method == 'POST':
        # process order creation here
        return redirect('order_history')
    return render(request, 'place_order.html')


def rate_chef(request, order_id):
    if request.method == 'POST':
        # handle rating submission
        return redirect('order_history')
    return render(request, 'rate_chef.html', {'order_id': order_id})


def file_complaint(request):
    if request.method == 'POST':
        # handle complaint submission
        return redirect('my_complaints')
    return render(request, 'file_complaint.html')


def file_compliment(request):
    if request.method == 'POST':
        # handle compliment submission
        return redirect('profile')
    return render(request, 'file_compliment.html')


def my_complaints(request):
    return render(request, 'my_complaints.html')


def available_orders(request):
    return render(request, 'available_orders.html')


def delivery_bid(request, order_id):
    if request.method == 'POST':
        # handle bid
        return redirect('available_orders')
    return render(request, 'delivery_bid.html', {'order_id': order_id})


def my_deliveries(request):
    return render(request, 'my_deliveries.html')


def chef_dashboard(request):
    return render(request, 'chef.html')


def manager_dashboard(request):
    return render(request, 'manager.html')

def discussions(request):
    return render(request, 'discussions.html')

def manage_menu(request):
    if request.method == 'POST':
        # handle menu changes
        return redirect('manage_menu')
    return render(request, 'manage_menu.html')


def review_complaint(request, complaint_id):
    if request.method == 'POST':
        # handle review action
        return redirect('my_complaints')
    return render(request, 'review_complaint.html', {'complaint_id': complaint_id})


def assign_order(request, order_id):
    if request.method == 'POST':
        # assign order logic
        return redirect('order_history')
    return render(request, 'assign_order.html', {'order_id': order_id})


def update_order_status(request, order_id):
    if request.method == 'POST':
        # update status logic
        return redirect('order_history')
    return redirect('order_history')
def login(request):
    if request.method == 'POST':
        name = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=name, password=password)
        if user is not None:
            # log the user in (create Django auth session)
            from django.contrib.auth import login as auth_login
            auth_login(request, user)

            # ensure our session key is set for legacy session usage
            request.session['user_id'] = user.id
            request.session.modified = True

            # ensure profile objects exist for this user type (create if missing)
            try:
                if getattr(user, 'type', None) == 'CU' and not Customer.objects.filter(login=user).exists():
                    Customer.objects.create(login=user)
                if getattr(user, 'type', None) == 'CH' and not Chef.objects.filter(login=user).exists():
                    Chef.objects.create(login=user)
                if getattr(user, 'type', None) == 'DL' and not Deliverer.objects.filter(login=user).exists():
                    Deliverer.objects.create(login=user)
                if getattr(user, 'type', None) == 'MN' and not Manager.objects.filter(login=user).exists():
                    Manager.objects.create(login=user)
            except Exception:
                # fail safe: don't block login on profile creation errors
                pass

            # Redirect to appropriate dashboard based on user type
            user_type = getattr(user, 'type', None)
            if user_type == 'CU':
                # Redirect to the customer page using query string (works with PA and local)
                return redirect(f"{reverse('customer')}?profile={user.username}")
            elif user_type == 'CH':
                return redirect('chef')
            elif user_type == 'DL':
                return redirect('deliverer')
            elif user_type == 'MN':
                return redirect('manager')
        else:
            messages.error(request, 'Invalid email or password.')
    return render(request, 'login.html')


def logout(request):
    """Log the user out and clear session-based user id, then show logout page."""
    # log out Django auth session (if any)
    try:
        auth_logout(request)
    except Exception:
        # ignore if logout fails for any reason
        pass

    # remove custom session key used in this project
    request.session.pop('user_id', None)
    request.session.modified = True

    messages.info(request, 'You have been logged out.')
    return render(request, 'logout.html')
def register(request):
    """Register a new user with validation and friendly errors.

    This uses Django's create_user to ensure passwords are hashed, sets the
    custom `type` field, logs the user in via Django's auth system, and
    creates the associated profile row for the chosen role (Customer/Chef/Deliverer/Manager).
    """
    USERTYPE = {'Customer': 'CU', 'Chef': 'CH', 'Deliverer': 'DL', 'Manager': 'MN'}

    if request.method == 'POST':
        role = request.POST.get('role', '')
        t = USERTYPE.get(role)
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        # Basic validation
        if not username or not email or not password or not t:
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'register.html', {'username': username, 'email': email, 'role': role})

        if DataUser.objects.filter(username=username).exists():
            messages.error(request, 'That username is already taken.')
            return render(request, 'register.html', {'username': username, 'email': email, 'role': role})

        if DataUser.objects.filter(email=email).exists():
            messages.error(request, 'An account with that email already exists.')
            return render(request, 'register.html', {'username': username, 'email': email, 'role': role})

        # Create the user and handle potential DB errors
        try:
            new_user = DataUser.objects.create_user(username=username, email=email, password=password)
            new_user.type = t
            new_user.save()
        except IntegrityError:
            messages.error(request, 'Unable to create account due to a database error. Please try again.')
            return render(request, 'register.html', {'username': username, 'email': email, 'role': role})

        # Log the user in via Django auth and set legacy session key.
        # Authenticate newly-created user so the auth backend is set, then login.
        try:
            auth_user = authenticate(request, username=username, password=password)
            if auth_user is not None:
                from django.contrib.auth import login as auth_login
                auth_login(request, auth_user)
                request.session['user_id'] = auth_user.id
            else:
                # fallback: set session id manually
                request.session['user_id'] = new_user.id
        except Exception:
            request.session['user_id'] = new_user.id

        request.session.modified = True

        # Create profile record for the chosen type if missing and redirect
        try:
            if t == 'CU':
                Customer.objects.create(login=new_user)
                return redirect('customer')
            if t == 'CH':
                Chef.objects.create(login=new_user)
                return redirect('chef')
            if t == 'DL':
                Deliverer.objects.create(login=new_user)
                return redirect('deliverer')
            if t == 'MN':
                Manager.objects.create(login=new_user)
                return redirect('manager')
        except Exception:
            messages.warning(request, 'Account created but profile initialization failed. Please contact support.')
            return redirect('index')

    return render(request, 'register.html')
def update_cart(request):
    return render(request, 'cart.html')
def cart(request):
    return render(request, 'cart.html')
def __getattr__(name):
    return lambda request, *args: render(request, f'{name}.html', *args)


def customer(request, profile: str = None):
    """Render a customer profile.

    Accepts either a querystring `?profile=<username>` or a path parameter
    `/customer/<profile>/`. Delegates to `profile_view` (which expects an
    integer `user_id`) by resolving the username to a user id.
    """
    # profile might come from path param or querystring
    profile = profile or request.GET.get('profile')
    if not profile:
        # If no profile provided, show a generic customer page or 404
        return render(request, 'customer.html')

    # try to resolve by username first, then by email
    user = DataUser.objects.filter(username=profile).first()
    if not user:
        user = DataUser.objects.filter(email=profile).first()
    if not user:
        # try numeric id
        try:
            user = DataUser.objects.get(id=int(profile))
        except Exception:
            user = None

    if not user:
        return get_object_or_404(DataUser, username=profile)  # will raise 404

    return profile_view(request, user.id)

def ai_chat(request):
    AI_PATH = "/home/SapphireBrick613/AI"
    if request.method != 'POST':
        return render(request, 'ai_chat')
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


def register(request):
    """Handle user registration with validation and graceful DB error handling."""
    USERTYPE = {'Customer': 'CU', 'Chef': 'CH', 'Deliverer': 'DL', 'Manager': 'MN'}

    if request.method == 'POST':
        role = request.POST.get('role', '')
        t = USERTYPE.get(role)
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')

        # Basic validation
        if not username or not email or not password or not t:
            messages.error(request, 'Please fill in all required fields.')
            return render(request, 'register.html', {'username': username, 'email': email, 'role': role})

        # Check duplicates and give friendly errors instead of raising DB constraint errors
        if DataUser.objects.filter(username=username).exists():
            messages.error(request, 'That username is already taken.')
            return render(request, 'register.html', {'username': username, 'email': email, 'role': role})
        if DataUser.objects.filter(email=email).exists():
            messages.error(request, 'An account with that email already exists.')
            return render(request, 'register.html', {'username': username, 'email': email, 'role': role})

        # Create user inside try/except to catch any integrity problems
        try:
            new_user = DataUser.objects.create_user(username=username, email=email, password=password)
            # store custom type on the model and save
            new_user.type = t
            new_user.save()
        except IntegrityError:
            messages.error(request, 'Unable to create account due to a database error. Please try again.')
            return render(request, 'register.html', {'username': username, 'email': email, 'role': role})

        # Log the user in by storing their ID in the session (your codebase uses session-based auth)
        request.session['user_id'] = new_user.id
        request.session.modified = True

        # Create profile records for specific user types and redirect to the appropriate dashboard
        match t:
            case 'CU':
                Customer.objects.create(login=new_user)
                return redirect('customer')
            case 'CH':
                Chef.objects.create(login=new_user)
                return redirect('chef')
            case 'DL':
                Deliverer.objects.create(login=new_user)
                return redirect('deliverer')
            case 'MN':
                Manager.objects.create(login=new_user)
                return redirect('manager')
            case _:
                messages.error(request, 'Invalid user type selected.')
                return render(request, 'register.html', {'username': username, 'email': email, 'role': role})

    return render(request, 'register.html')