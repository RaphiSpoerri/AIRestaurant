

from django.db.models import *

from .users import Employee
from .chef import Dish


class Order(Model):
    id = AutoField(primary_key=True)

class OrderedDish(Model):
    from_order_num = ForeignKey(Order, CASCADE)
    dish = OneToOneField(Dish, CASCADE)
    quantity = IntegerField()

    def total_cost(self) -> int:
        return self.dish.price * self.quantity
    

class Deliverer(Employee):
    pass