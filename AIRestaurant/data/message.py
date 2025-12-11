


from django.db.models import *
from .users import User

class Thread(Model):
    id            = AutoField(primary_key=True)
    title         = CharField(max_length=100)
    creation_date = DateTimeField()

class Message(Model):
    thread  = ForeignKey(Thread, CASCADE, null=False)
    message = CharField(max_length=256, null=False)
    who     = ForeignKey(User, SET_NULL, null=True)
    when    = DateTimeField(null=False)

class Compliment(Model):
    sender  = ForeignKey(User, SET_NULL, related_name="ComplimentSender", null=True)
    to      = ForeignKey(User, CASCADE, related_name="ComplimentTo", null=True)
    message = ForeignKey(Message, CASCADE)

class Complaint(Model):
    STATUS = [
        ('v', 'valid'),
        ('p', 'pending'),
        ('i', 'invalid')
    ]
    sender  = ForeignKey(User, SET_NULL, related_name="ComplaintSender", null=True)
    to      = ForeignKey(User, CASCADE, related_name="ComplaintTo", null=True)
    message = ForeignKey(Message, CASCADE)
    # use short code 'p' to match STATUS choices
    status  = CharField(max_length=1, choices=STATUS, default='p')
