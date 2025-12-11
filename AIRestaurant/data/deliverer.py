

from django.db.models import *

from .users import Employee, User
from .chef import Product


class Order(Model):
    id = AutoField(primary_key=True)
    # Link to the Customer model in the same Django app
    customer = ForeignKey("Customer", CASCADE, null=True, blank=True)
    date = DateTimeField(auto_now_add=True)
    status = CharField(max_length=20, default="pending")
    # Null => deliverer pending; set when manager assigns
    assigned_deliverer = ForeignKey(
        User,
        on_delete=SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_orders",
    )
    # Classify orders so each one is either food or merch
    order_type = CharField(
        max_length=5,
        choices=[("food", "Food"), ("merch", "Merch")],
        default="food",
    )


class OrderedDish(Model):
    from_order_num = ForeignKey(Order, CASCADE, related_name="items")
    product = ForeignKey(Product, CASCADE)
    quantity = IntegerField()

    def total_cost(self) -> int:
        return self.product.price * self.quantity


class Deliverer(Employee):
    pass


class Bid(Model):
        """A deliverer's bid (or abstention) for delivering a specific order.

        - Each Bid links a deliverer (via their User record) to an Order.
        - `price_cents` stores the bid amount in cents; it may be null to
            indicate the deliverer is abstaining from bidding.
        """

        order = ForeignKey(Order, CASCADE, related_name="bids")
        deliverer = ForeignKey(User, CASCADE, related_name="delivery_bids")
        price_cents = IntegerField(null=True, blank=True)
        created_at = DateTimeField(auto_now_add=True)

        class Meta:
                unique_together = ("order", "deliverer")