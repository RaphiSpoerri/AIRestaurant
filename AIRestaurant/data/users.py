

from django.db.models import *

class User(Model):
    name        = CharField(max_length=40)
    email       = CharField(max_length=40)
    password    = CharField(max_length=40)

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
        TODO: should return (COUNT(good)  - COUNT(bad)) where
        good = (SELECT * FROM Compliment AS c WHERE c.to == self.login)
        bad  = (SELECT * FROM Complaint AS c WHERE c.to == self.login AND c.status == 'valid')
        """
        raise NotImplementedError()

