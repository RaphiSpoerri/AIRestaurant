from django.shortcuts import render
from django.http import JsonResponse
import json
from subprocess import run as shell
from urllib.parse import unquote
from django.shortcuts import get_object_or_404
from types import SimpleNamespace
from .models import (
    User as DataUser,
    Customer,
    ProductRating,
    Product,
    Deliverer,
    Chef,
    Manager,
    Compliment,
    Complaint,
    Message,
    Employee,
    Order,
    OrderedDish,
    Plea,
    FAQEntry,
    Bid,
)
from django.db.models import Avg, Count
from django.utils import timezone
from django.shortcuts import redirect
from django.contrib import messages
from django.db import IntegrityError
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .data.message import Thread
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.urls import reverse
from .faq import search_entries, create_entry, tokenize

def home(request):
    return render(request, 'index.html', {'user': request.user})
def menu(request):
    """Show menu with rating metadata for each dish.

    Provides per-dish average rating and rating count, and exposes a
    simple `can_rate` flag used by the template for logged-in customers.
    """
    dishes_qs = Product.objects.filter(type='food').annotate(
        avg_rating=Avg('productrating__rating'),
        rating_count=Count('productrating')
    )

    is_customer = (
        request.user.is_authenticated and
        getattr(request.user, 'type', None) == 'CU'
    )

    # Look at any in-progress cart stored in the session so the
    # quantities shown on the menu reflect what is already in the cart.
    session_cart = request.session.get('cart', {}) or {}

    # Attach convenient attributes used by the template
    dishes = []
    for d in dishes_qs:
        d.average_rating = (d.avg_rating or 0)
        d.rating_count = d.rating_count
        d.can_rate = is_customer
        # Initial quantity for this dish based on the cart
        try:
            d.initial_qty = int(session_cart.get(str(d.id), 0))
        except (TypeError, ValueError):
            d.initial_qty = 0
        dishes.append(d)

    return render(request, 'menu.html', {'dishes': dishes, 'enable_cart': True})


def merch(request):
    """Show restaurant merchandise using the shared product list layout.

    Merch items are stored as `Product` rows tagged with type='merch'.
    """
    products_qs = Product.objects.filter(type='merch').annotate(
        avg_rating=Avg('productrating__rating'),
        rating_count=Count('productrating'),
    )

    # Reuse the same session-based cart; quantities reflect in-progress merch
    session_cart = request.session.get('cart', {}) or {}

    merch_items = []
    for p in products_qs:
        p.average_rating = p.avg_rating or 0
        p.rating_count = p.rating_count
        p.can_rate = False
        try:
            p.initial_qty = int(session_cart.get(str(p.id), 0))
        except (TypeError, ValueError):
            p.initial_qty = 0
        merch_items.append(p)

    return render(request, 'merch.html', {'dishes': merch_items, 'enable_cart': True})
def add_to_cart(request):
    return render(request, 'cart.html')

@csrf_exempt
@require_POST
def rate_dish(request, dish_id):
    """Receive an AJAX rating for a dish and persist it.

    For now we treat ratings as per-customer using the Employee model as a
    generic "rater" record keyed by the Django User.
    """
    # Allow any authenticated user to rate dishes; primary restriction is login.
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'You must be logged in to rate dishes.'}, status=403)

    try:
        rating_val = int(request.POST.get('rating', '0'))
    except ValueError:
        return JsonResponse({'error': 'Invalid rating value.'}, status=400)

    if rating_val < 1 or rating_val > 5:
        return JsonResponse({'error': 'Rating must be between 1 and 5.'}, status=400)

    try:
        dish = get_object_or_404(Product, pk=dish_id)

        # Ensure we have an Employee record linked to this user so
        # ProductRating(unique_together=(product, who)) can store per-user ratings.
        rater, _ = Employee.objects.get_or_create(login=request.user)

        # Use a safer update pattern to avoid issues if duplicate
        # ProductRating rows ever exist.
        dr = ProductRating.objects.filter(product=dish, who=rater).first()
        if dr is None:
            dr = ProductRating(product=dish, who=rater)
        dr.rating = rating_val
        dr.save()

        # Recompute aggregate rating info to return to the client if needed
        agg = ProductRating.objects.filter(product=dish).aggregate(avg=Avg('rating'), count=Count('id'))
        return JsonResponse({
            'status': 'ok',
            'dish_id': dish.id,
            'average_rating': agg['avg'] or 0,
            'rating_count': agg['count'] or 0,
        })
    except Exception as e:
        # Surface the underlying error so the frontend can display it
        return JsonResponse({'error': f'Internal error while saving rating: {e}'}, status=500)

def deposit(request):
    # Ensure user is authenticated and is a customer
    if not request.user.is_authenticated:
        messages.error(request, 'Please log in to access the deposit page.')
        return redirect('login')
    
    try:
        customer = Customer.objects.get(login=request.user)
    except Customer.DoesNotExist:
        messages.error(request, 'Customer profile not found.')
        return redirect('index')
    
    if request.method == 'POST':
        amount_str = request.POST.get('amount', '0').strip()
        try:
            # Convert dollars to cents
            amount_cents = int(float(amount_str) * 100)
            if amount_cents <= 0:
                raise ValueError("Amount must be positive.")
        except ValueError:
            messages.error(request, 'Please enter a valid positive amount.')
            return render(request, 'deposit.html', {'customer': customer, 'form': {'amount': amount_str}})

        # Update user balance
        customer.balance += amount_cents
        customer.save()

        messages.success(request, f'Successfully deposited ${amount_cents / 100:.2f} to your account.')
        return redirect('deposit')

    return render(request, 'deposit.html', {'customer': customer, 'form': {}})

def rate_ai_response(request, rating_id):
    """Stub: record a rating for an AI response and return JSON."""
    if request.method == 'POST':
        # placeholder: in real app, save rating to DB
        return JsonResponse({'status': 'ok', 'rating_id': rating_id})
    return JsonResponse({'error': 'POST required'}, status=400)


def remove_from_cart(request, menu_id):
    """Remove a dish from the session-based cart and redirect back."""
    if request.method == 'POST':
        cart = request.session.get('cart', {}) or {}
        cart.pop(str(menu_id), None)
        request.session['cart'] = cart
        request.session.modified = True
    return redirect('cart')


def place_order(request):
    """Finalize an order: persist Order/OrderedDish and charge balance."""
    if request.method != 'POST':
        messages.error(request, 'Use the checkout form to place an order.')
        return redirect('cart')

    if not request.user.is_authenticated or getattr(request.user, 'type', None) != 'CU':
        messages.error(request, 'Only logged-in customers can place orders.')
        return redirect('login')

    try:
        customer = Customer.objects.get(login=request.user)
    except Customer.DoesNotExist:
        messages.error(request, 'Customer profile not found.')
        return redirect('index')

    cart = request.session.get('cart', {}) or {}
    if not cart:
        messages.error(request, 'Your cart is empty.')
        return redirect('menu')

    # Compute total in cents based on product prices and prepare OrderedDish list
    dish_ids = [int(did) for did in cart.keys()]
    dishes = {d.id: d for d in Product.objects.filter(id__in=dish_ids)}

    total_cents = 0
    ordered_rows = []
    order_type = None
    cart_mixed = False
    for dish_id_str, qty in cart.items():
        try:
            qty = int(qty)
        except (TypeError, ValueError):
            qty = 0
        if qty <= 0:
            continue
        dish = dishes.get(int(dish_id_str))
        if not dish:
            continue
        p_type = getattr(dish, 'type', 'food')
        if order_type is None:
            order_type = p_type
        elif order_type != p_type:
            cart_mixed = True
        total_cents += dish.price * qty
        ordered_rows.append(OrderedDish(product=dish, quantity=qty))

    if total_cents <= 0 or not ordered_rows:
        messages.error(request, 'Unable to calculate order total.')
        return redirect('cart')

    if cart_mixed:
        messages.error(request, 'You cannot place a mixed food and merch order. Please separate them into different orders.')
        return redirect('cart')

    if customer.balance < total_cents:
        # Not enough balance: add a warning
        customer.add_warning()

        # If this pushed the customer into suspended status, redirect to the
        # suspension notice and remember which account is suspended via a
        # dedicated cookie (independent of the auth session).
        if customer.login.status == 'SU':
            response = redirect('suspended_notice')
            response.set_cookie('suspended_user_id', str(customer.login.id), max_age=3600, httponly=True, samesite='Lax')
            return response

        messages.error(request, 'Insufficient balance. Your warning count has increased by one.')
        return redirect('cart')

    # Use the domain method to create an Order and charge balance
    try:
        order = customer.order(ordered_rows, order_type=order_type or "food")
        order.customer = customer
        order.save()
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('cart')

    # Clear cart after successful charge
    request.session['cart'] = {}
    request.session.modified = True

    messages.success(request, f'Order placed successfully for ${total_cents / 100:.2f}.')
    return redirect('order_history')


def rate_chef(request, order_id):
    if request.method == 'POST':
        # handle rating submission
        return redirect('order_history')
    return render(request, 'rate_chef.html', {'order_id': order_id})


def suspended_notice(request):
    """Show a suspension notice to customers flagged as suspended.

    Allows them to submit a plea message to managers. We track the
    suspended account via a dedicated cookie so that even after logging
    out of the current auth session, we can still associate the plea
    with the correct User record.
    """
    suspended_user = None
    suspended_id = request.COOKIES.get('suspended_user_id')
    need_set_cookie = False

    # Try to resolve suspended account from the cookie first.
    if suspended_id:
        try:
            suspended_user = DataUser.objects.filter(pk=int(suspended_id)).first()
        except (TypeError, ValueError):
            suspended_user = None

    # Fallback: if no cookie yet but the request user is a suspended
    # customer, treat them as the suspended account and arrange to set
    # the cookie in the response.
    if suspended_user is None and request.user.is_authenticated:
        if getattr(request.user, 'type', None) == 'CU' and getattr(request.user, 'status', 'AC') == 'SU':
            suspended_user = request.user
            need_set_cookie = True

    # Validate that we actually have a suspended customer account.
    if suspended_user is None or getattr(suspended_user, 'type', None) != 'CU':
        messages.error(request, 'Suspension notices are only for customer accounts.')
        return redirect('index')

    if getattr(suspended_user, 'status', 'AC') != 'SU':
        return redirect('index')

    plea_created = False
    if request.method == 'POST':
        plea = request.POST.get('plea', '').strip()
        if plea:
            Plea.objects.create(sender=suspended_user, text=plea)
            messages.success(request, 'Your message has been sent to the manager for review.')
            plea_created = True
        else:
            messages.error(request, 'Please enter a message before submitting.')

    # Once the notice has been shown, log out any active auth session so
    # the suspended account no longer appears as logged in.
    if request.user.is_authenticated:
        try:
            auth_logout(request)
        except Exception:
            pass

    response = render(request, 'suspended_notice.html', {'suspended_user': suspended_user})

    # Ensure the suspended id cookie is set for subsequent POSTs if it
    # wasn't already present.
    if need_set_cookie:
        response.set_cookie('suspended_user_id', str(suspended_user.id), max_age=3600, httponly=True, samesite='Lax')

    # After a successful plea submission, we can drop the cookie.
    if plea_created:
        response.delete_cookie('suspended_user_id')

    return response


def review_complaint(request, complaint_id):
    """Manager action: mark a complaint as valid or invalid.

    This view is intended to be called via POST from the manager dashboard
    with a `decision` field set to either "accept" or "reject".
    """
    viewer = request.user
    viewer_type = getattr(viewer, 'type', None)
    is_manager = getattr(viewer, 'is_staff', False) or getattr(viewer, 'is_superuser', False) or (viewer_type == 'MN')

    if not is_manager:
        messages.error(request, 'Only managers can review complaints.')
        return redirect('index')

    complaint = get_object_or_404(Complaint, pk=complaint_id)

    if request.method == 'POST':
        decision = request.POST.get('decision')
        if decision == 'accept':
            complaint.status = 'v'
            complaint.save(update_fields=['status'])
            messages.success(request, 'Complaint has been marked as valid.')
            # Apply side effects for employees (chef/deliverer) when a
            # complaint is confirmed as valid. This may demote or fire
            # them once their score reaches the configured thresholds.
            target_user = complaint.to
            employee = None
            if getattr(target_user, 'type', None) == 'CH':
                employee = Chef.objects.filter(login=target_user).first()
            elif getattr(target_user, 'type', None) == 'DL':
                employee = Deliverer.objects.filter(login=target_user).first()
            if employee is not None:
                # Run side effects to update status/salary based on the
                # new valid complaint. This will demote or fire employees
                # once their score crosses the configured thresholds.
                employee.add_complaint_sideaffects()
        elif decision == 'reject':
            complaint.status = 'i'
            complaint.save(update_fields=['status'])
            messages.success(request, 'Complaint has been marked as invalid.')
        else:
            messages.error(request, 'Unknown decision for complaint review.')

        return redirect('profile', user_id=viewer.id)

    # For non-POST access, just send the manager back to their profile.
    return redirect('profile', user_id=viewer.id)


@require_POST
def plea_kick(request, plea_id):
    """Manager action: permanently remove a suspended user and their plea."""
    viewer = request.user
    viewer_type = getattr(viewer, 'type', None)
    is_manager = getattr(viewer, 'is_staff', False) or getattr(viewer, 'is_superuser', False) or (viewer_type == 'MN')

    if not is_manager:
        messages.error(request, 'Only managers can process pleas.')
        return redirect('index')

    plea = get_object_or_404(Plea, pk=plea_id)
    user = plea.sender
    username = user.username

    # Delete the user; related Customer and other rows will cascade
    user.delete()
    plea.delete()

    messages.success(request, f'User {username} has been removed and their plea closed.')
    return redirect('profile', user_id=viewer.id)


@require_POST
def plea_forgive(request, plea_id):
    """Manager action: reduce warnings, reactivate account, and close plea."""
    viewer = request.user
    viewer_type = getattr(viewer, 'type', None)
    is_manager = getattr(viewer, 'is_staff', False) or getattr(viewer, 'is_superuser', False) or (viewer_type == 'MN')

    if not is_manager:
        messages.error(request, 'Only managers can process pleas.')
        return redirect('index')

    plea = get_object_or_404(Plea, pk=plea_id)
    user = plea.sender

    customer = Customer.objects.filter(login=user).first()
    if customer:
        if customer.warnings > 0:
            customer.warnings -= 1
        customer.save()

    # Reactivate account
    user.status = 'AC'
    user.save(update_fields=['status'])

    plea.delete()

    messages.success(request, f'User {user.username} has been reactivated and their warnings reduced.')
    return redirect('profile', user_id=viewer.id)


def file_complaint(request):
    """File a complaint using the shared _complaint_form partial.

    - From order history: /file_complaint/?order_id=<id>
    - From profile pages: the partial is embedded directly there.
    """
    if not request.user.is_authenticated:
        messages.error(request, 'Please log in to file a complaint.')
        return redirect('login')

    target = None
    order_id = request.GET.get('order_id')
    if order_id:
        try:
            order = Order.objects.get(pk=int(order_id))
        except (Order.DoesNotExist, ValueError, TypeError):
            order = None
        if order:
            # Simple policy: complaints about orders go to the manager
            mgr = Manager.objects.first()
            target = getattr(mgr, 'login', None)

    return render(request, 'file_complaint.html', {
        'target': target,
    })


def file_compliment(request):
    """Send a compliment using the shared _compliment_form partial.

    - From order history: /file_compliment/?order_id=<id>
    - From profile pages: the partial is embedded directly there.
    """
    if not request.user.is_authenticated:
        messages.error(request, 'Please log in to send a compliment.')
        return redirect('login')

    target = None
    order_id = request.GET.get('order_id')
    if order_id:
        try:
            order = Order.objects.get(pk=int(order_id))
        except (Order.DoesNotExist, ValueError, TypeError):
            order = None
        if order:
            mgr = Manager.objects.first()
            target = getattr(mgr, 'login', None)
        
    return render(request, 'file_compliment.html', {
        'target': target,
    })


def assign_order(request, order_id):
    """Manager view to review bids for an order and assign it.

    For now this view focuses on displaying all bids. Assignment
    itself can be wired up later.
    """
    viewer = request.user
    viewer_type = getattr(viewer, 'type', None)
    is_manager = getattr(viewer, 'is_staff', False) or getattr(viewer, 'is_superuser', False) or (viewer_type == 'MN')

    if not is_manager:
        messages.error(request, 'Only managers can assign orders.')
        return redirect('index')

    order = get_object_or_404(
        Order.objects.select_related('customer__login').prefetch_related('items__product', 'bids__deliverer'),
        pk=order_id,
    )

    # Compute total in dollars for display
    total_cents = 0
    for item in order.items.all():
        try:
            total_cents += item.total_cost()
        except Exception:
            if getattr(item, 'product', None) is not None and item.quantity:
                total_cents += item.product.price * item.quantity
    order.total_amount = total_cents / 100.0

    # All bids for this order, with a convenient dollars field
    bids = list(order.bids.all().select_related('deliverer'))
    for b in bids:
        b.bid_amount = None
        if b.price_cents is not None:
            b.bid_amount = b.price_cents / 100.0

    if request.method == 'POST':
        # Placeholder: in the future, we can persist the chosen deliverer
        delivery_person_id = request.POST.get('delivery_person_id')
        if not delivery_person_id:
            messages.error(request, 'Please choose a delivery person to assign this order.')
            return render(request, 'assign_order.html', {'order': order, 'bids': bids})

        messages.success(request, 'Order assignment choice recorded (implementation pending).')
        return redirect('manager')

    return render(request, 'assign_order.html', {'order': order, 'bids': bids})


def update_order_status(request, order_id):
    if request.method == 'POST':
        # update status logic
        return redirect('order_history')
    return redirect('order_history')
def order_history(request):
    """Show the current customer's past orders with items and totals."""
    if not request.user.is_authenticated or getattr(request.user, 'type', None) != 'CU':
        messages.error(request, 'Please log in as a customer to view your order history.')
        return redirect('login')

    try:
        customer = Customer.objects.get(login=request.user)
    except Customer.DoesNotExist:
        messages.error(request, 'Customer profile not found.')
        return redirect('index')

    orders = Order.objects.filter(customer=customer).prefetch_related('items__product').order_by('-date')

    # For compatibility with the existing template, annotate simple totals
    for o in orders:
        total_cents = sum(od.total_cost() for od in o.items.all())
        o.total_amount = total_cents / 100.0
        # Template expects `timestamp`; alias our `date` field
        o.timestamp = o.date

    return render(request, 'order_history.html', {'orders': orders})
def login(request):
    if request.method == 'POST':
        name = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=name, password=password)
        if user is not None:
            # Check if account is active (manager approval status)
            status = getattr(user, 'status', 'AC')
            if status != 'AC':
                if status == 'PN':
                    messages.error(request, 'Your account is pending manager approval. Please wait for approval.')
                elif status == 'SU':
                    # Distinguish between suspended customers and fired staff.
                    fired = False
                    user_type = getattr(user, 'type', None)
                    if user_type in ('CH', 'DL'):
                        employee = None
                        if user_type == 'CH':
                            employee = Chef.objects.filter(login=user).first()
                        elif user_type == 'DL':
                            employee = Deliverer.objects.filter(login=user).first()
                        if employee is not None and getattr(employee, 'status', None) == 'FD':
                            fired = True

                    if fired:
                        messages.error(request, 'Your account has been terminated. You have been fired.')
                    else:
                        messages.error(request, 'Your account has been suspended.')
                else:
                    messages.error(request, 'Your account is not active.')
                return render(request, 'login.html')
            
            # log the user in (create Django auth session)
            from django.contrib.auth import login as auth_login
            auth_login(request, user)

            # ensure our session key is set for legacy session usage
            request.session['user_id'] = user.id
            request.session.modified = True

            # Redirect to the unified profile view for this user id.
            # The profile view chooses the correct template based on user.type
            # (customer/chef/deliverer/manager) so the correct data is shown.
            return redirect('profile', user_id=user.id)
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

def update_cart(request):
    """Store the current cart (dish id -> quantity) in the session.

    Expects a POST with a JSON-encoded `cart` payload from menu.js.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    if not request.user.is_authenticated or getattr(request.user, 'type', None) != 'CU':
        return JsonResponse({'error': 'Only logged-in customers can use the cart.'}, status=403)

    cart_json = request.POST.get('cart', '{}')
    try:
        cart_data = json.loads(cart_json)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid cart payload.'}, status=400)

    # Normalize quantities to integers >= 0
    normalized = {}
    for dish_id, qty in cart_data.items():
        try:
            qty_int = int(qty)
        except (TypeError, ValueError):
            continue
        if qty_int > 0:
            normalized[str(dish_id)] = qty_int

    request.session['cart'] = normalized
    request.session.modified = True
    return JsonResponse({'status': 'ok'})


def cart(request):
    """Render the cart page based on the session cart contents."""
    if not request.user.is_authenticated or getattr(request.user, 'type', None) != 'CU':
        messages.error(request, 'Please log in as a customer to view your cart.')
        return redirect('login')

    try:
        customer = Customer.objects.get(login=request.user)
    except Customer.DoesNotExist:
        messages.error(request, 'Customer profile not found.')
        return redirect('index')

    session_cart = request.session.get('cart', {}) or {}
    if not session_cart:
        return render(request, 'cart.html', {
            'cart': {},
            'total': 0,
            'customer': customer,
            'cart_type': None,
            'cart_mixed': False,
        })

    dish_ids = [int(did) for did in session_cart.keys()]
    dishes = {d.id: d for d in Product.objects.filter(id__in=dish_ids)}

    cart_items = {}
    total_cents = 0
    cart_type = None
    cart_mixed = False
    for dish_id_str, qty in session_cart.items():
        try:
            qty = int(qty)
        except (TypeError, ValueError):
            continue
        if qty <= 0:
            continue
        dish = dishes.get(int(dish_id_str))
        if not dish:
            continue
        # Track whether this cart is food-only or merch-only
        p_type = getattr(dish, 'type', 'food')
        if cart_type is None:
            cart_type = p_type
        elif cart_type != p_type:
            cart_mixed = True
        price_cents = dish.price
        subtotal_cents = price_cents * qty
        total_cents += subtotal_cents
        cart_items[int(dish_id_str)] = {
            'name': dish.name,
            'price': price_cents,
            'quantity': qty,
            'subtotal': subtotal_cents,
        }

    return render(request, 'cart.html', {
        'cart': cart_items,
        'total': total_cents,
        'customer': customer,
        'cart_type': cart_type,
        'cart_mixed': cart_mixed,
    })

def chef(request):
    """Redirect to current user's chef profile if authenticated."""
    if request.user.is_authenticated:
        return redirect('profile', user_id=request.user.id)
    return render(request, 'chef.html')


def available_orders(request):
    """List all pending orders that are available for delivery.

    Currently we treat any order with status="pending" as unassigned
    and therefore available. Only logged-in deliverers can view this
    page.
    """
    if not request.user.is_authenticated:
        messages.error(request, 'Please log in to view available orders.')
        return redirect('login')

    if getattr(request.user, 'type', None) != 'DL':
        messages.error(request, 'Only deliverers can view available orders.')
        return redirect('index')

    orders_qs = (
        Order.objects
        .filter(status='pending')
        .select_related('customer__login')
        .prefetch_related('items__product')
        .order_by('-date')
    )

    orders = []
    for order in orders_qs:
        total_cents = 0
        for item in order.items.all():
            try:
                total_cents += item.total_cost()
            except Exception:
                if getattr(item, 'product', None) is not None and item.quantity:
                    total_cents += item.product.price * item.quantity
        order.total_amount = total_cents / 100.0
        orders.append(order)

    return render(request, 'available_orders.html', {'orders': orders})


def delivery_bid(request, order_id):
    """Allow a deliverer to place an optional bid on an order.

    For now we simply validate the input and show a success message;
    orders remain in the pool of available orders.
    """
    if not request.user.is_authenticated:
        messages.error(request, 'Please log in to place a delivery bid.')
        return redirect('login')

    if getattr(request.user, 'type', None) != 'DL':
        messages.error(request, 'Only deliverers can place delivery bids.')
        return redirect('index')

    order = get_object_or_404(
        Order.objects.select_related('customer__login').prefetch_related('items__product', 'bids__deliverer'),
        pk=order_id,
    )

    # Compute a display total in dollars from line items
    total_cents = 0
    for item in order.items.all():
        try:
            total_cents += item.total_cost()
        except Exception:
            if getattr(item, 'product', None) is not None and item.quantity:
                total_cents += item.product.price * item.quantity
    order.total_amount = total_cents / 100.0

    # Existing bid (if any) from this deliverer for this order
    existing_bid = Bid.objects.filter(order=order, deliverer=request.user).first()

    if request.method == 'POST':
        bid_raw = (request.POST.get('bid_amount') or '').strip()
        bid_amount = None

        if bid_raw:
            try:
                bid_amount = float(bid_raw)
                if bid_amount < 0:
                    raise ValueError()
            except ValueError:
                messages.error(request, 'Please enter a valid non-negative bid amount.')
                return render(request, 'delivery_bid.html', {
                    'order': order,
                    'bid_amount': bid_raw,
                })

        # Convert dollars to cents; None means abstaining
        price_cents = None
        if bid_amount is not None:
            price_cents = int(round(bid_amount * 100))

        bid_obj, _created = Bid.objects.get_or_create(
            order=order,
            deliverer=request.user,
            defaults={'price_cents': price_cents},
        )
        if not _created:
            bid_obj.price_cents = price_cents
            bid_obj.save(update_fields=['price_cents'])

        if bid_amount is not None:
            messages.success(
                request,
                f'Your bid of ${bid_amount:.2f} for order #{order.id} has been recorded.',
            )
        else:
            messages.success(
                request,
                f'Your abstention for order #{order.id} has been recorded.',
            )

        return redirect('available_orders')

    # Pre-fill the form with any existing bid (in dollars)
    initial_bid = ''
    if existing_bid and existing_bid.price_cents is not None:
        initial_bid = f"{existing_bid.price_cents / 100:.2f}"

    return render(request, 'delivery_bid.html', {'order': order, 'bid_amount': initial_bid})


def deliverer(request):
    """Redirect to current user's deliverer profile if authenticated."""
    if request.user.is_authenticated:
        return redirect('profile', user_id=request.user.id)
    return render(request, 'deliverer.html')

def manager(request):
    """Redirect to current user's manager profile if authenticated."""
    if request.user.is_authenticated:
        return redirect('profile', user_id=request.user.id)
    return render(request, 'manager.html', {'user': request.user, 'pending_users': DataUser.objects.filter(status='PN')})

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
    if request.method != 'POST':
        return render(request, 'ai_chat.html')
    if "testing":
        question = unquote(request.POST.get('query'))
        result = shell(
            [f'llama-run', f'/Users/raphispoerri/College/csc322/tinyllama-1.1b-chat-v1.0.Q4_0.gguf'],
            capture_output=True,
            input=question,
            encoding='utf-8')
    else:
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
        # employee-related metrics (for chefs/deliverers)
        'employee': None,
        'employee_score': None,
        'employee_salary_dollars': None,
        'employee_bonus_dollars': None,
        'employee_demotion_dollars': None,
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

    # compliments and complaints (show all for full history, latest first)
    context['compliments'] = list(
        Compliment.objects
        .filter(to=target)
        .select_related('sender', 'message')
        .order_by('-id')
    )
    context['complaints'] = list(
        Complaint.objects
        .filter(to=target)
        .select_related('sender', 'message')
        .order_by('-id')
    )

    # compute average product rating for chefs (food items only) and
    # employee metrics (salary, promotion status, net score) for
    # chefs and deliverers.
    if target.type in ('CH', 'DL'):
        # employee profile instance (Chef/Deliverer subclass Employee)
        employee = context['profile']

        # Chef-specific average dish rating
        if target.type == 'CH':
            try:
                avg = ProductRating.objects.filter(
                    product__type='food',
                    product__creator__login=target,
                ).aggregate(avg=Avg('rating'))['avg']
                if avg is not None:
                    context['avg_dish_rating'] = round(avg, 2)
            except Exception:
                context['avg_dish_rating'] = None

        # Employee metrics if we have a backing Employee record
        if employee is not None:
            try:
                score_val = employee.score()
            except Exception:
                score_val = None

            context.update({
                'employee': employee,
                'employee_score': score_val,
                'employee_salary_dollars': (employee.salary or 0) / 100.0,
                'employee_bonus_dollars': (employee.bonus or 0) / 100.0,
                'employee_demotion_dollars': (employee.demotion or 0) / 100.0,
            })

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

    # For managers, include pending registration requests, pleas, complaints,
    # and any customer orders that are still pending.
    if target.type == 'MN':
        context['pending_users'] = list(DataUser.objects.filter(status='PN').order_by('date_joined'))
        context['pleas'] = list(Plea.objects.select_related('sender').order_by('-created_at'))
        # Show all complaints that are in a pending state. Some older
        # rows may have string 'pending', newer ones use the short code 'p'.
        context['pending_complaints'] = list(
            Complaint.objects.filter(status__in=['p', 'pending'])
            .select_related('sender', 'to', 'message')
            .order_by('-id')
        )

        # Pending orders: all orders with status='pending'. At the moment
        # there is no explicit deliverer assignment on the Order model, so
        # "unassigned" and "pending" are equivalent.
        context['pending_orders'] = list(
            Order.objects.filter(status='pending')
            .select_related('customer')
            .order_by('-date')
        )

    # pick template by target type
    tpl_map = {'CU': 'customer.html', 'CH': 'chef.html', 'DL': 'deliverer.html', 'MN': 'manager.html'}
    tpl = tpl_map.get(target.type, 'customer.html')

    return render(request, tpl, context)


def discussions(request):
    """List recent threads and support searching by title via GET param `q`.

    For improved UX we pass along per-thread metadata so the template can
    display a message count and a short preview of the latest message.
    """
    q = request.GET.get('q', '').strip()
    if q:
        threads_qs = Thread.objects.filter(title__icontains=q).order_by('-creation_date')[:50]
    else:
        threads_qs = Thread.objects.all().order_by('-creation_date')[:10]

    # Build a lightweight list of dicts with thread + activity metadata
    threads = []
    for t in threads_qs:
        last_msg = Message.objects.filter(thread=t).select_related('who').order_by('-when').first()
        count = Message.objects.filter(thread=t).count()
        threads.append({
            'thread': t,
            'count': count,
            'last': last_msg,
        })

    return render(request, 'discussions.html', {
        'threads': threads,
        'query': q,
    })


def manage_users(request):
    """Manager-only view listing all users and their key details.

    Shows account status, role, and any associated profile/employee metrics
    to help managers make informed decisions.
    """
    viewer = request.user
    viewer_type = getattr(viewer, 'type', None)
    is_manager = getattr(viewer, 'is_staff', False) or getattr(viewer, 'is_superuser', False) or (viewer_type == 'MN')

    if not is_manager:
        messages.error(request, 'Only managers can view the user management page.')
        return redirect('index')

    users = list(
        DataUser.objects.all()
        .order_by('id')
    )

    # Preload related profile/employee objects
    from .data.customer import Customer as CustomerProfile
    from .data.chef import Chef as ChefProfile
    from .data.deliverer import Deliverer as DelivererProfile
    from .data.manager import Manager as ManagerProfile

    customer_map = {c.login_id: c for c in CustomerProfile.objects.all()}
    chef_map = {c.login_id: c for c in ChefProfile.objects.all()}
    deliverer_map = {d.login_id: d for d in DelivererProfile.objects.all()}
    manager_map = {m.login_id: m for m in ManagerProfile.objects.all()}

    # Attach lightweight profile info per user for the template
    user_rows = []
    for u in users:
        profile = None
        employee = None
        extra = {}

        if u.type == 'CU':
            profile = customer_map.get(u.id)
            if profile is not None:
                extra = {
                    'warnings': profile.warnings,
                    'balance_cents': profile.balance,
                    'vip': profile.vip,
                }
        elif u.type == 'CH':
            profile = chef_map.get(u.id)
            employee = profile
        elif u.type == 'DL':
            profile = deliverer_map.get(u.id)
            employee = profile
        elif u.type == 'MN':
            profile = manager_map.get(u.id)

        if employee is not None:
            try:
                score_val = employee.score()
            except Exception:
                score_val = None
            extra.update({
                'employee_status': employee.get_status_display(),
                'employee_salary_dollars': (employee.salary or 0) / 100.0,
                'employee_score': score_val,
            })

        user_rows.append({
            'user': u,
            'profile': profile,
            'extra': extra,
        })

    return render(request, 'manage_users.html', {
        'viewer': viewer,
        'user_rows': user_rows,
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
        'thread_messages': messages_qs,
    })


def register(request):
    """Register a new user with pending approval status.
    
    Creates a User account with status='PN' (Pending Approval) but does NOT:
    - Automatically create profile records (Customer/Chef/Deliverer/Manager)
    - Log the user in or create a session
    
    Manager approval is required to activate the account and create profiles.
    """
    # Map roles from the registration form to internal codes
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

        # Create user with pending approval status
        try:
            new_user = DataUser.objects.create_user(username=username, email=email, password=password)
            # Set type and status (pending approval by manager)
            new_user.type = t
            new_user.status = 'PN'  # Pending Approval
            new_user.save()
        except IntegrityError:
            messages.error(request, 'Unable to create account due to a database error. Please try again.')
            return render(request, 'register.html', {'username': username, 'email': email, 'role': role})

        # Show success message and redirect to login
        messages.success(request, 'Account created successfully. Please wait for manager approval before logging in.')
        return redirect('login')

    return render(request, 'register.html')


@require_POST
def approve_user(request, user_id):
    """Manager approves a pending user registration and creates their profile."""
    # Verify requester is a manager
    viewer = request.user
    viewer_type = getattr(viewer, 'type', None)
    is_manager = getattr(viewer, 'is_staff', False) or getattr(viewer, 'is_superuser', False) or (viewer_type == 'MN')
    
    if not is_manager:
        messages.error(request, 'Only managers can approve user registrations.')
        return redirect('index')
    
    try:
        user = DataUser.objects.get(id=user_id, status='PN')
    except DataUser.DoesNotExist:
        messages.error(request, 'User not found or already approved.')
        return redirect('index')
    
    # Activate the user and create profile
    try:
        user.status = 'AC'
        user.save()
        
        # Create profile record for the chosen type
        if user.type == 'CU':
            Customer.objects.create(login=user)
        elif user.type == 'CH':
            Chef.objects.create(login=user)
        elif user.type == 'DL':
            Deliverer.objects.create(login=user)
        elif user.type == 'MN':
            Manager.objects.create(login=user)
        
        messages.success(request, f'User {user.username} approved and profile created.')
    except Exception as e:
        messages.error(request, f'Error approving user: {str(e)}')
    
    # Redirect back to manager profile
    return redirect('profile', user_id=viewer.id)


@require_POST
def reject_user(request, user_id):
    """Manager rejects a pending registration and deletes the user account."""
    viewer = request.user
    viewer_type = getattr(viewer, 'type', None)
    is_manager = getattr(viewer, 'is_staff', False) or getattr(viewer, 'is_superuser', False) or (viewer_type == 'MN')

    if not is_manager:
        messages.error(request, 'Only managers can reject user registrations.')
        return redirect('index')

    try:
        user = DataUser.objects.get(id=user_id, status='PN')
    except DataUser.DoesNotExist:
        messages.error(request, 'User not found or already processed.')
        return redirect('profile', user_id=viewer.id)

    username = user.username
    try:
        user.delete()
        messages.success(request, f'User {username} rejected and removed.')
    except Exception as e:
        messages.error(request, f'Error rejecting user: {str(e)}')

    return redirect('profile', user_id=viewer.id)


def faq(request):
    """FAQ page with search and inform functionality."""
    search_query = request.GET.get('q', '').strip()
    
    # Always show all entries, or filter by search
    if search_query:
        all_entries = search_entries(search_query)
    else:
        all_entries = FAQEntry.objects.all()
    
    duplicate_warning = None
    
    # Handle new FAQ submission (logged-in users only)
    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, 'You must be logged in to add FAQ entries.')
            return redirect('login')
        
        question = request.POST.get('question', '').strip()
        answer = request.POST.get('answer', '').strip()
        force_submit = request.POST.get('force_submit') == 'true'
        
        if question and answer:
            # Check for duplicates (90% word overlap)
            existing = search_entries(question)
            
            if existing and not force_submit:
                # Warn about duplicates
                duplicate_warning = {
                    'question': question,
                    'answer': answer,
                    'similar': existing
                }
            else:
                # Create new entry
                create_entry(question, answer, request.user)
                messages.success(request, 'FAQ entry added successfully!')
                return redirect('faq')
        else:
            messages.error(request, 'Both question and answer are required.')
    
    return render(request, 'faq.html', {
        'search_query': search_query,
        'all_entries': all_entries,
        'duplicate_warning': duplicate_warning,
        # Always pass the current query so AI can answer alongside results
        'initial_query': search_query,
    })
