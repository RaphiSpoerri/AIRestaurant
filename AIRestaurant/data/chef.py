

from django.db.models import *
from .users import Employee
from .customer import Customer
class Chef(Employee):
    pass

class Dish(Model):
    name    = CharField(max_length=50)
    price   = PositiveIntegerField()
    chef    = ForeignKey(Chef, CASCADE)

class DishRating(Model):
    dish    = ForeignKey(Dish, CASCADE)
    who     = ForeignKey(Customer, CASCADE)
    rating  = IntegerField()

