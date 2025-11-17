

from django.db.models import *
from .users import Employee

class Chef(Employee):
    def create_dish(self, name, price):
        # TODO: create a Dish object and call .save()
        raise NotImplementedError()

class Dish(Model):
    name    = CharField(max_length=50)
    price   = PositiveIntegerField()
    chef    = ForeignKey(Chef, CASCADE)
