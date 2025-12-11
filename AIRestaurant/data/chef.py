

from django.db.models import *
from .users import Employee

class Chef(Employee):
    pass

class Dish(Model):
    name    = CharField(max_length=50)
    img     = CharField(max_length=256, default="?")
    price   = PositiveIntegerField()
    chef    = ForeignKey(Chef, CASCADE)

class DishRating(Model):
    dish    = ForeignKey(Dish, CASCADE)
    who     = ForeignKey(Employee, CASCADE)
    rating  = IntegerField()
    
    class Meta:
        unique_together = ('dish', 'who')