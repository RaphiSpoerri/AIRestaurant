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
    """Home page with restaurant information"""
    return render(request, 'restaurant/index.html')


def menu(request):
    """Menu page with all available dishes"""
    search = request.GET.get('search', '')
    category = request.GET.get('category', '')
    
    menu_items = Menu.objects.filter(is_available=True)
    
    if search:
        menu_items = menu_items.filter(Q(name__icontains=search) | Q(description__icontains=search))
    if category:
        menu_items = menu_items.filter(category=category)
    
    categories = Menu.objects.values_list('category', flat=True).distinct().exclude(category='')
    
    # Add average rating and rating count to each menu item
    menu_items = menu_items.annotate(
        average_rating=Avg('ratings__rating'),
        rating_count=Count('ratings')
    )
    
    context = {
        'dishes': menu_items,
        'search': search,
        'category': category,
        'categories': categories,
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
        if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            rating = get_object_or_404(AIResponseRating, id=rating_id)
            rating_value = request.POST.get('rating')
            
            if rating_value in ['1', '2', '3', '4', '5']:
                rating.rating = int(rating_value)
                rating.save()
                return JsonResponse({'status': 'success'})
    except Exception as e:
        messages.error(request, f'Error submitting rating: {str(e)}')
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)


@login_required
def rate_dish(request, dish_id):
    """Handle dish rating submission"""
    if request.method == 'POST' and request.user.is_authenticated:
        try:
            dish = Menu.objects.get(id=dish_id)
            rating_value = int(request.POST.get('rating', 0))
            
            if not (1 <= rating_value <= 5):
                return JsonResponse({'status': 'error', 'message': 'Invalid rating value'}, status=400)
            
            # Update or create rating
            rating, created = Rating.objects.update_or_create(
                user=request.user,
                dish=dish,
                defaults={'rating': rating_value}
            )
            
            # Calculate new average rating
            ratings = Rating.objects.filter(dish=dish)
            average_rating = ratings.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0
            
            return JsonResponse({
                'status': 'success', 
                'average_rating': round(float(average_rating), 1),
                'rating_count': ratings.count()
            })
            
        except Menu.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Dish not found'}, status=404)
        except (ValueError, TypeError):
            return JsonResponse({'status': 'error', 'message': 'Invalid rating value'}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

@login_required
def update_cart(request):
    """Update the user's cart"""
    if request.method == 'POST' and request.user.is_authenticated:
        try:
            import json
            cart_data = json.loads(request.POST.get('cart', '{}'))
            
            # Validate cart data
            if not isinstance(cart_data, dict):
                return JsonResponse({'status': 'error', 'message': 'Invalid cart data'}, status=400)
            
            # Update cart in session or database
            if hasattr(request, 'session'):
                request.session['cart'] = cart_data
                request.session.modified = True
                return JsonResponse({'status': 'success', 'message': 'Cart updated successfully'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Session not available'}, status=500)
                
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid JSON data'}, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)