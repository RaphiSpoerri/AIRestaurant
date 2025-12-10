

from django.db.models import *
from .users import Employee

class Chef(Employee):
    def create_dish(self, name, img):
        # TODO: create a Dish object, setting price to "null", and call .save()
        raise NotImplementedError()

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