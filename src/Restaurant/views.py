from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Sum, Count, Avg
from django.db import transaction
from .models import (
    User, Menu, Order, OrderItem, Complaint, Compliment, Rating, 
    Warning, Blacklist, DeliveryBid, KnowledgeBaseEntry, AIResponseRating
)
from .forms import MenuItemForm, ComplaintForm, ComplimentForm, RatingForm, DeliveryBidForm, DepositForm
from .utils import (
    calculate_vip_status, process_complaint_decision, get_user_total_spending,
    can_user_place_order, is_user_blacklisted
)
import json


def index(request):
    """Home page with menu browsing"""
    search = request.GET.get('search', '')
    category = request.GET.get('category', '')
    
    menu_items = Menu.objects.filter(is_available=True)
    
    if search:
        menu_items = menu_items.filter(Q(name__icontains=search) | Q(description__icontains=search))
    if category:
        menu_items = menu_items.filter(category=category)
    
    categories = Menu.objects.values_list('category', flat=True).distinct().exclude(category='')
    
    context = {
        'menu_items': menu_items,
        'search': search,
        'category': category,
        'categories': categories,
    }
    return render(request, 'restaurant/index.html', context)


def login_view(request):
    """User login"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user and user.is_active:
            login(request, user)
            return redirect('index')
        else:
            messages.error(request, 'Invalid username or password, or account is inactive.')
    
    return render(request, 'restaurant/login.html')


def logout_view(request):
    """User logout"""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('index')


def register(request):
    """User registration"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role', 'Customer')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return redirect('register')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return redirect('register')
        
        user = User.objects.create_user(username=username, email=email, password=password, role=role)
        messages.success(request, 'Registration successful! Please wait for manager approval.')
        return redirect('login')
    
    return render(request, 'restaurant/register.html')


# Role-based access decorators
def manager_required(view_func):
    return user_passes_test(lambda u: u.is_manager, login_url='index')(view_func)


def customer_required(view_func):
    return user_passes_test(lambda u: u.is_authenticated and u.is_customer, login_url='login')(view_func)


def chef_required(view_func):
    return user_passes_test(lambda u: u.is_chef, login_url='index')(view_func)


def delivery_required(view_func):
    return user_passes_test(lambda u: u.is_delivery, login_url='index')(view_func)


@login_required
@customer_required
def cart(request):
    """View shopping cart"""
    cart_data = request.session.get('cart', {})
    # Calculate subtotals for display
    cart_with_subtotals = {}
    for menu_id, item in cart_data.items():
        item_copy = item.copy()
        item_copy['subtotal'] = item['price'] * item['quantity']
        cart_with_subtotals[menu_id] = item_copy
    
    total = sum(item['price'] * item['quantity'] for item in cart_data.values())
    
    context = {
        'cart': cart_with_subtotals,
        'total': total,
    }
    return render(request, 'restaurant/cart.html', context)


@login_required
@customer_required
def add_to_cart(request, menu_id):
    """Add item to shopping cart"""
    menu_item = get_object_or_404(Menu, id=menu_id, is_available=True)
    
    cart = request.session.get('cart', {})
    quantity = int(request.POST.get('quantity', 1))
    
    if str(menu_id) in cart:
        cart[str(menu_id)]['quantity'] += quantity
    else:
        cart[str(menu_id)] = {
            'name': menu_item.name,
            'price': float(menu_item.price),
            'quantity': quantity,
        }
    
    request.session['cart'] = cart
    messages.success(request, f'{menu_item.name} added to cart.')
    return redirect('index')


@login_required
@customer_required
def remove_from_cart(request, menu_id):
    """Remove item from cart"""
    cart = request.session.get('cart', {})
    cart.pop(str(menu_id), None)
    request.session['cart'] = cart
    messages.info(request, 'Item removed from cart.')
    return redirect('cart')


@login_required
@customer_required
def place_order(request):
    """Place an order"""
    can_order, error_msg = can_user_place_order(request.user)
    if not can_order:
        messages.error(request, error_msg)
        return redirect('cart')
    
    cart = request.session.get('cart', {})
    if not cart:
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart')
    
    # Calculate total
    total = sum(item['price'] * item['quantity'] for item in cart.values())
    
    # Check balance
    if request.user.balance < total:
        messages.error(request, 'Insufficient balance. Please deposit money first.')
        return redirect('cart')
    
    # Create order
    with transaction.atomic():
        order = Order.objects.create(
            customer=request.user,
            total_amount=total,
            delivery_address=request.POST.get('delivery_address', ''),
            notes=request.POST.get('notes', ''),
            status='Pending'
        )
        
        # Create order items
        for menu_id, item_data in cart.items():
            menu_item = get_object_or_404(Menu, id=int(menu_id))
            OrderItem.objects.create(
                order=order,
                menu_item=menu_item,
                quantity=item_data['quantity'],
                subtotal=item_data['price'] * item_data['quantity']
            )
        
        # Deduct balance
        request.user.balance -= total
        request.user.save()
        
        # Clear cart
        request.session['cart'] = {}
        
        # Check VIP status
        calculate_vip_status(request.user)
        
        messages.success(request, f'Order #{order.id} placed successfully!')
        return redirect('order_history')


@login_required
@customer_required
def order_history(request):
    """View order history"""
    orders = Order.objects.filter(customer=request.user).order_by('-timestamp')
    return render(request, 'restaurant/order_history.html', {'orders': orders})


@login_required
@customer_required
def deposit(request):
    """Deposit money to account"""
    if request.method == 'POST':
        form = DepositForm(request.POST)
        if form.is_valid():
            amount = form.cleaned_data['amount']
            request.user.balance += amount
            request.user.save()
            messages.success(request, f'${amount:.2f} deposited successfully. New balance: ${request.user.balance:.2f}')
            return redirect('deposit')
    else:
        form = DepositForm()
    
    return render(request, 'restaurant/deposit.html', {'form': form})


@login_required
def file_complaint(request):
    """File a complaint"""
    if request.method == 'POST':
        form = ComplaintForm(request.POST)
        if form.is_valid():
            complaint = form.save(commit=False)
            complaint.filed_by = request.user
            complaint.save()
            messages.success(request, 'Complaint filed successfully. Manager will review it.')
            return redirect('my_complaints')
    else:
        form = ComplaintForm()
        # Filter orders for dropdown
        if request.user.is_customer:
            form.fields['order'].queryset = Order.objects.filter(customer=request.user)
            # Get users from orders for filed_against
            order_ids = Order.objects.filter(customer=request.user).values_list('id', flat=True)
            from .models import User
            form.fields['filed_against'].queryset = User.objects.filter(
                Q(orders_received__in=order_ids) | Q(orders_delivered__in=order_ids)
            ).distinct()
        else:
            form.fields['order'].queryset = Order.objects.none()
            form.fields['filed_against'].queryset = User.objects.none()
    
    return render(request, 'restaurant/file_complaint.html', {'form': form})


@login_required
def file_compliment(request):
    """File a compliment"""
    if request.method == 'POST':
        form = ComplimentForm(request.POST)
        if form.is_valid():
            compliment = form.save(commit=False)
            compliment.filed_by = request.user
            compliment.save()
            messages.success(request, 'Compliment submitted successfully!')
            return redirect('index')
    else:
        form = ComplimentForm()
        if request.user.is_customer:
            form.fields['order'].queryset = Order.objects.filter(customer=request.user)
            # Get users from orders for filed_against (chefs and delivery people)
            order_ids = Order.objects.filter(customer=request.user).values_list('id', flat=True)
            # Get chefs from menu items in orders
            menu_items = Menu.objects.filter(order_items__order_id__in=order_ids).distinct()
            chefs = User.objects.filter(menu_items__in=menu_items, role='Chef').distinct()
            # Get delivery people from orders
            delivery_people = User.objects.filter(orders_delivered__id__in=order_ids, role='DeliveryPerson').distinct()
            # Combine
            form.fields['filed_against'].queryset = (chefs | delivery_people).distinct()
        else:
            form.fields['order'].queryset = Order.objects.none()
            form.fields['filed_against'].queryset = User.objects.none()
    
    return render(request, 'restaurant/file_compliment.html', {'form': form})


@login_required
def my_complaints(request):
    """View user's filed complaints"""
    complaints = Complaint.objects.filter(filed_by=request.user).order_by('-created_at')
    return render(request, 'restaurant/my_complaints.html', {'complaints': complaints})


@login_required
@customer_required
def rate_chef(request, order_id):
    """Rate chef after order delivery"""
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    
    if order.status != 'Delivered':
        messages.warning(request, 'You can only rate delivered orders.')
        return redirect('order_history')
    
    # Get unique menu items with chefs from this order
    menu_items_with_chefs = []
    seen_chefs = set()
    for order_item in order.items.all():
        menu_item = order_item.menu_item
        if menu_item.chef and menu_item.chef.id not in seen_chefs:
            menu_items_with_chefs.append(menu_item)
            seen_chefs.add(menu_item.chef.id)
    
    if request.method == 'POST':
        # Handle rating submission
        chef_id = request.POST.get('chef')
        menu_item_id = request.POST.get('menu_item')
        rating_value = request.POST.get('rating')
        comment = request.POST.get('comment', '')
        
        chef = get_object_or_404(User, id=chef_id, role='Chef')
        menu_item = get_object_or_404(Menu, id=menu_item_id) if menu_item_id else None
        
        # Check if rating already exists
        existing_rating = Rating.objects.filter(
            order=order,
            chef=chef,
            customer=request.user
        ).first()
        
        if existing_rating:
            existing_rating.rating = int(rating_value)
            existing_rating.comment = comment
            if menu_item:
                existing_rating.menu_item = menu_item
            existing_rating.save()
        else:
            Rating.objects.create(
                order=order,
                chef=chef,
                customer=request.user,
                menu_item=menu_item,
                rating=int(rating_value),
                comment=comment
            )
        
        messages.success(request, 'Rating submitted successfully!')
        return redirect('order_history')
    
    return render(request, 'restaurant/rate_chef.html', {
        'order': order, 
        'menu_items': menu_items_with_chefs
    })


@login_required
@delivery_required
def available_orders(request):
    """View orders available for bidding"""
    orders = Order.objects.filter(
        status__in=['Ready', 'Pending'],
        delivery_person__isnull=True
    )
    return render(request, 'restaurant/available_orders.html', {'orders': orders})


@login_required
@delivery_required
def delivery_bid(request, order_id):
    """Place a bid on an order for delivery"""
    order = get_object_or_404(Order, id=order_id)
    
    if order.delivery_person:
        messages.warning(request, 'This order already has a delivery person assigned.')
        return redirect('available_orders')
    
    if request.method == 'POST':
        form = DeliveryBidForm(request.POST)
        if form.is_valid():
            bid = form.save(commit=False)
            bid.order = order
            bid.delivery_person = request.user
            bid.save()
            messages.success(request, 'Bid placed successfully!')
            return redirect('available_orders')
    else:
        form = DeliveryBidForm()
    
    return render(request, 'restaurant/delivery_bid.html', {'order': order, 'form': form})


@login_required
@delivery_required
def my_deliveries(request):
    """View assigned delivery orders"""
    orders = Order.objects.filter(delivery_person=request.user).order_by('-timestamp')
    return render(request, 'restaurant/my_deliveries.html', {'orders': orders})


@login_required
@chef_required
def chef_dashboard(request):
    """Chef dashboard"""
    orders = Order.objects.filter(
        items__menu_item__chef=request.user
    ).distinct().order_by('-timestamp')
    
    # Get chef's average rating
    avg_rating = Rating.objects.filter(chef=request.user).aggregate(avg=Avg('rating'))['avg'] or 0.0
    
    return render(request, 'restaurant/chef_dashboard.html', {
        'orders': orders,
        'avg_rating': round(avg_rating, 2)
    })


@login_required
@manager_required
def manager_dashboard(request):
    """Manager dashboard"""
    pending_complaints = Complaint.objects.filter(status='Pending')
    pending_compliments = Compliment.objects.filter(status='Pending')
    pending_orders = Order.objects.filter(
        status__in=['Ready', 'Pending'],
        delivery_person__isnull=True
    )
    flagged_kb = KnowledgeBaseEntry.objects.filter(flagged=True)
    bids = DeliveryBid.objects.filter(status='Pending')
    
    return render(request, 'restaurant/manager_dashboard.html', {
        'pending_complaints': pending_complaints,
        'pending_compliments': pending_compliments,
        'pending_orders': pending_orders,
        'flagged_kb': flagged_kb,
        'bids': bids,
    })


@login_required
@manager_required
def review_complaint(request, complaint_id):
    """Manager reviews and decides on complaint"""
    complaint = get_object_or_404(Complaint, id=complaint_id)
    
    if request.method == 'POST':
        decision = request.POST.get('decision')
        notes = request.POST.get('notes', '')
        process_complaint_decision(complaint, decision, notes)
        messages.success(request, f'Complaint {decision.lower()}ed.')
        return redirect('manager_dashboard')
    
    return render(request, 'restaurant/review_complaint.html', {'complaint': complaint})


@login_required
@manager_required
def assign_order(request, order_id):
    """Manager assigns order to delivery person based on bids"""
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        delivery_person_id = request.POST.get('delivery_person_id')
        delivery_person = get_object_or_404(User, id=delivery_person_id, role='DeliveryPerson')
        
        order.delivery_person = delivery_person
        order.status = 'Out for Delivery'
        order.save()
        
        # Mark bid as accepted
        bid = DeliveryBid.objects.filter(order=order, delivery_person=delivery_person).first()
        if bid:
            bid.status = 'Accepted'
            bid.save()
        
        # Reject other bids
        DeliveryBid.objects.filter(order=order, status='Pending').update(status='Rejected')
        
        messages.success(request, 'Order assigned successfully.')
        return redirect('manager_dashboard')
    
    bids = DeliveryBid.objects.filter(order=order, status='Pending')
    return render(request, 'restaurant/assign_order.html', {'order': order, 'bids': bids})


@login_required
def update_order_status(request, order_id):
    """Update order status (for chefs and delivery people)"""
    order = get_object_or_404(Order, id=order_id)
    new_status = request.POST.get('status')
    
    # Check permissions
    can_update = False
    if request.user.is_manager:
        can_update = True
    elif request.user.is_chef and order.status in ['Pending', 'Preparing']:
        # Chef can only update if they have items in the order
        if order.items.filter(menu_item__chef=request.user).exists():
            can_update = True
    elif request.user.is_delivery and order.delivery_person == request.user:
        can_update = True
    
    if can_update and new_status in ['Pending', 'Preparing', 'Ready', 'Out for Delivery', 'Delivered']:
        order.status = new_status
        order.save()
        messages.success(request, f'Order status updated to {new_status}.')
    else:
        messages.error(request, 'You do not have permission to update this order.')
    
    if request.user.is_delivery:
        return redirect('my_deliveries')
    elif request.user.is_chef:
        return redirect('chef_dashboard')
    else:
        return redirect('manager_dashboard')


@login_required
@manager_required
def manage_menu(request):
    """Manager interface to manage menu items"""
    menu_items = Menu.objects.all().order_by('name')
    chefs = User.objects.filter(role='Chef', is_active=True)
    
    if request.method == 'POST':
        if 'add' in request.POST:
            form = MenuItemForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                messages.success(request, f'Menu item "{form.cleaned_data["name"]}" added successfully!')
                return redirect('manage_menu')
            else:
                messages.error(request, 'Please correct the errors below.')
        elif 'update' in request.POST:
            menu_id = request.POST.get('menu_id')
            menu_item = get_object_or_404(Menu, id=menu_id)
            form = MenuItemForm(request.POST, request.FILES, instance=menu_item)
            if form.is_valid():
                # Handle image update - if no new image provided, keep the old one
                if 'image' not in request.FILES or not request.FILES['image']:
                    form.instance.image = menu_item.image
                form.save()
                messages.success(request, f'Menu item "{menu_item.name}" updated successfully!')
                return redirect('manage_menu')
            else:
                messages.error(request, 'Please correct the errors below.')
    else:
        form = MenuItemForm()
    
    return render(request, 'restaurant/manage_menu.html', {
        'menu_items': menu_items,
        'chefs': chefs,
        'form': form
    })


@login_required
def ai_chat(request):
    """AI customer service chat"""
    if request.method == 'POST':
        query = request.POST.get('query')
        if query:
            from .ai_service import get_ai_service
            ai_service = get_ai_service()
            user = request.user if request.user.is_authenticated else None
            response = ai_service.get_ai_response(query, user)
            return JsonResponse(response)
    
    return render(request, 'restaurant/ai_chat.html')


@login_required
def rate_ai_response(request, rating_id):
    """Rate an AI response"""
    try:
        rating_value = int(request.POST.get('rating', 0))
        if rating_value < 0 or rating_value > 5:
            messages.error(request, 'Invalid rating value.')
            return redirect('ai_chat')
        
        from .ai_service import get_ai_service
        ai_service = get_ai_service()
        
        if ai_service.rate_ai_response(rating_id, rating_value):
            messages.success(request, 'Thank you for your feedback!')
        else:
            messages.error(request, 'Failed to submit rating.')
    except Exception as e:
        messages.error(request, f'Error submitting rating: {str(e)}')
    
    return redirect('ai_chat')
