
from django.db.models import *
from typing import *
from .users import User, Employee
from .deliverer import OrderedDish
from .chef import Dish

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

    
    def order(self, dishes: List[OrderedDish]):
        """Create an `Order` with `OrderedDish` rows and charge balance.

        Expects a list of *unsaved* `OrderedDish` instances with `dish` and
        `quantity` set. This method will:
          - compute the total cost in cents,
          - ensure the customer has sufficient balance,
          - create an `Order` row,
          - attach and save each `OrderedDish` to that order,
          - deduct the total from this customer's balance.

        Returns the created `Order` instance.
        Raises ValueError if balance is insufficient or the order is invalid.
        """
        from .deliverer import Order  # local import to avoid cycles

        if not dishes:
            raise ValueError("No dishes provided for order.")

        total_cost = 0
        for od in dishes:
            if od.dish is None or od.quantity is None:
                continue
            if od.quantity <= 0:
                continue
            total_cost += od.total_cost()

        if total_cost <= 0:
            raise ValueError("Order total must be positive.")

        if self.balance < total_cost:
            raise ValueError("Insufficient balance for this order.")

        # Create the order and attach dishes
        order = Order.objects.create()
        for od in dishes:
            if od.dish is None or od.quantity is None or od.quantity <= 0:
                continue
            od.from_order_num = order
            od.save()

        # Charge the customer
        self.balance -= total_cost
        self.save()

        return order

