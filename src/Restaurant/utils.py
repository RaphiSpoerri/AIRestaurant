from django.db.models import Sum
from django.utils import timezone
from .models import Order, Complaint, Warning, Blacklist


def calculate_vip_status(user):
    """
    Check if user qualifies for VIP status:
    - Total spending > $100 OR
    - 3 orders without complaints
    Auto-promote if criteria met.
    """
    if not user or user.role in ['Chef', 'DeliveryPerson', 'Manager']:
        return False
    
    # Check if already VIP
    if user.role == 'VIP':
        return True
    
    # Check total spending
    total_spent = Order.objects.filter(
        customer=user,
        status='Delivered'
    ).aggregate(total=Sum('total_amount'))['total'] or 0.0
    
    if total_spent > 100.0:
        user.role = 'VIP'
        user.save()
        return True
    
    # Check for 3 orders without complaints
    delivered_orders = Order.objects.filter(
        customer=user,
        status='Delivered'
    )
    
    if delivered_orders.count() >= 3:
        # Check if any of these orders have approved complaints
        order_ids = delivered_orders.values_list('id', flat=True)
        approved_complaints = Complaint.objects.filter(
            order_id__in=order_ids,
            status='Approved'
        ).count()
        
        if approved_complaints == 0:
            user.role = 'VIP'
            user.save()
            return True
    
    return False


def process_complaint_decision(complaint, manager_decision, manager_notes=None):
    """
    Process manager's decision on a complaint.
    If rejected: issue warning to filer
    Count warnings: 2 warnings (VIP) = demote, 3 warnings (any) = blacklist
    """
    complaint.status = 'Approved' if manager_decision == 'Approved' else 'Rejected'
    complaint.manager_decision = manager_decision
    complaint.manager_notes = manager_notes
    complaint.reviewed_at = timezone.now()
    complaint.save()
    
    # If complaint is rejected, issue warning to the person who filed it
    if manager_decision == 'Rejected':
        warning = Warning.objects.create(
            user=complaint.filed_by,
            reason=f"Rejected complaint: {complaint.description[:100]}",
            complaint=complaint
        )
        
        # Count warnings for the user
        warning_count = Warning.objects.filter(user=complaint.filed_by).count()
        filer = complaint.filed_by
        
        # Check if user should be demoted or blacklisted
        if warning_count >= 3:
            # Blacklist user
            Blacklist.objects.update_or_create(
                user=filer,
                defaults={'reason': '3 warnings issued for rejected complaints'}
            )
            filer.is_active = False
            filer.save()
        
        elif warning_count >= 2 and filer.role == 'VIP':
            # Demote VIP to Customer
            filer.role = 'Customer'
            filer.save()
    
    return True


def get_user_warning_count(user):
    """Get the number of warnings for a user."""
    return Warning.objects.filter(user=user).count()


def is_user_blacklisted(user):
    """Check if a user is blacklisted."""
    return Blacklist.objects.filter(user=user).exists()


def get_user_total_spending(user):
    """Calculate total amount spent by a user."""
    total = Order.objects.filter(
        customer=user,
        status='Delivered'
    ).aggregate(total=Sum('total_amount'))['total'] or 0.0
    return float(total)


def get_user_order_count(user):
    """Get total number of delivered orders for a user."""
    return Order.objects.filter(
        customer=user,
        status='Delivered'
    ).count()


def can_user_place_order(user):
    """Check if user can place an order (not blacklisted, has sufficient balance, etc.)"""
    if is_user_blacklisted(user):
        return False, "You are blacklisted and cannot place orders."
    
    if not user.is_active:
        return False, "Your account is not active."
    
    return True, None

