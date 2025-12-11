

from django.db.models import *
from .users import Employee


class Chef(Employee):
    pass


class Product(Model):
    name = CharField(max_length=50)
    img = CharField(max_length=256, default="?")
    price = PositiveIntegerField()
    # When true, this item is only visible/orderable to VIP customers.
    vip_exclusive = BooleanField(default=False)
    # Classify products so we can distinguish menu items from merch
    type = CharField(
        max_length=10,
        choices=[("food", "Food"), ("merch", "Merch")],
        default="food",
    )
    # Creator is typically a Chef for food items; merch can be anonymous
    creator = ForeignKey(Chef, CASCADE, null=True, blank=True)


class ProductRating(Model):
    product = ForeignKey(Product, CASCADE)
    who = ForeignKey(Employee, CASCADE)
    rating = IntegerField()

    class Meta:
        unique_together = ("product", "who")