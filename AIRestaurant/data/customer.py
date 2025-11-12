
from django.db.models import *

from .users import User

class Customer(Model):
    login       = ForeignKey(User, on_delete=CASCADE)
    warnings    = PositiveIntegerField()
    balance     = PositiveIntegerField()
    vip         = BooleanField()