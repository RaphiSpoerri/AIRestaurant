

from django.db.models import *
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    id          = AutoField(primary_key=True)
    username    = CharField(max_length=40, unique=True, default="")
    email       = CharField(max_length=40, unique=True)
    password    = CharField(max_length=40)
    type        = CharField(max_length=2, choices=[
        ('CU', 'Customer'),
        ('DL', 'Deliverer'),
        ('CH', 'Chef'),
        ('MN', 'Manager')], default="CU")

class Employee(Model):
    login       = OneToOneField(User, CASCADE)
    balance     = IntegerField()
    salary      = IntegerField()
    bonus       = IntegerField() # fixed amount 
    demotion    = IntegerField() # salary when demoted

    def average_rating(self):
        """
        TODO: should return AVG(SELECT score FROM Rating AS r WHERE r.to == self.login)
        """
        raise NotImplementedError()


    def score(self):
        """
        TODO: should return good + good_vip - bad - bad_vip
        good = (SELECT COUNT(*) FROM Compliment AS c WHERE c.to == self.login)
        bad  = (SELECT COUNT(*) FROM Complaint AS c WHERE c.to == self.login AND c.status == 'valid')
        good_vip = (SELECT COUNT(*) FROM Compliment AS c
            INNER JOIN Customer
            ON c.sender == Customer.login AND c.vip AND c.to == self.login)
        bad_vip = (SELECT COUNT(*) FROM Compliment AS c
            INNER JOIN Customer
            ON c.sender == Customer.login AND c.vip AND c.to == self.login AND c.status == 'valid)
        """
        raise NotImplementedError()

