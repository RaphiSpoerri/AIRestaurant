
from django.db.models import *
from .users import User

class Manager(Model):
    login   = OneToOneField(User, CASCADE)