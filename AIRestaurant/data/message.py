


from django.db.models import *
from .users import User

class Thread(Model):
    title         = CharField(max_length=100)
    creation_date = DateTimeField()

class Message(Model):
    thread  = ForeignKey(Thread, CASCADE) # can be null if not in a thread
    message = CharField(max_length=256, null=False)
    who     = ForeignKey(User, CASCADE, null=False)
    when    = DateTimeField(null=False)

class Compliment(Model):
    to      = ForeignKey(User, CASCADE)
    message = ForeignKey(Message, CASCADE)

class Complaint(Model):
    STATUS = [
        ('v', 'valid'),
        ('p', 'pending'),
        ('i', 'invalid')
    ]
    to      = ForeignKey(User, CASCADE)
    message = ForeignKey(Message, CASCADE)
    status  = CharField(max_length=1, choices=STATUS, default='pending')
