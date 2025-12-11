
from django.db.models import *
from typing import *
from .users import User, Employee

from .chef import Product

class Customer(Model):
    login       = ForeignKey(User, on_delete=CASCADE)
    warnings    = PositiveIntegerField(default=0)
    balance     = PositiveIntegerField(default=0)  # in cents
    vip         = BooleanField(default=False)

    def complain_about(self, person: Union['Customer', Employee], message: str):
        # TODO: create a Complaint object and save it
        raise NotImplementedError()

    def add_warning(self):
        self.warnings += 1
        if not self.vip:
            if self.warnings == 3:
                # Suspend customer account and let the manager decide as whether 
                # to kick out the customer or give them another chance
                self.login.status = 'SU'
                # Persist the status change on the underlying auth user
                self.login.save(update_fields=["status"])
        elif self.warnings == 2:
            self.warnings = 0
            self.vip = False

        self.save()

    
    def order(self, dishes: List[OrderedDish], order_type: str = "food"):
        """Create an `Order` with `OrderedDish` rows and charge balance.

        `order_type` must be either "food" or "merch" and marks the
        classification of this order.

        Expects a list of *unsaved* `OrderedDish` instances with `product`
        and `quantity` set. This method will:
          - compute the total cost in cents,
          - ensure the customer has sufficient balance,
          - create an `Order` row with the appropriate type,
          - attach and save each `OrderedDish` to that order,
          - deduct the total from this customer's balance.

        Returns the created `Order` instance.
        Raises ValueError if balance is insufficient or the order is invalid.
        """
        from .deliverer import Order  # local import to avoid cycles
        from .message import Complaint

        if order_type not in ("food", "merch"):
            raise ValueError("order_type must be 'food' or 'merch'.")

        if not dishes:
            raise ValueError("No items provided for order.")

        total_cost = 0
        for od in dishes:
            if getattr(od, "product", None) is None or od.quantity is None:
                continue
            if od.quantity <= 0:
                continue
            total_cost += od.total_cost()

        # Apply VIP discount: 5% off the order total for VIP customers.
        # This affects how much is charged, but not the underlying
        # line-item prices stored on the order.
        if self.vip and total_cost > 0:
            discount = (total_cost * 5) // 100
            total_cost -= discount

        if total_cost <= 0:
            raise ValueError("Order total must be positive.")

        if self.balance < total_cost:
            raise ValueError("Insufficient balance for this order.")

        # Create the order and attach line items
        order = Order.objects.create(customer=self, order_type=order_type)
        for od in dishes:
            if getattr(od, "product", None) is None or od.quantity is None or od.quantity <= 0:
                continue
            od.from_order_num = order
            od.save()

        # Charge the customer
        self.balance -= total_cost
        self.save()

        # VIP upgrade logic:
        # After each successful order, if this customer either
        #   - has made at least 3 purchases total, or
        #   - has spent at least $100 (10_000 cents) in total,
        # and there are no valid complaints about them, they
        # become VIP.
        if not self.vip:
            has_valid_complaints = Complaint.objects.filter(
                to=self.login,
                status='v',
            ).exists()

            if not has_valid_complaints:
                # Consider all orders for this customer.
                orders_qs = Order.objects.filter(customer=self)
                order_count = orders_qs.count()

                total_spent_cents = 0
                for o in orders_qs.prefetch_related('items__product'):
                    for item in o.items.all():
                        total_spent_cents += item.total_cost()

                if order_count >= 3 or total_spent_cents >= 10000:
                    self.vip = True
                    self.save(update_fields=['vip'])

        return order

