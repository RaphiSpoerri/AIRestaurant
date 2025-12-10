

from django.db.models import *
from django.contrib.auth.models import AbstractUser



class User(AbstractUser):
    id          = AutoField(primary_key=True)
    username    = CharField(max_length=40, unique=True, default="")
    email       = CharField(max_length=40, unique=True)
    password    = CharField(max_length=40)
    status      = CharField(max_length=2, choices=[
        ('AC', 'Active'),
        ('SU', 'Suspended'),
        ('PN', 'Pending Approval')], default='PN')
    type        = CharField(max_length=2, choices=[
        ('CU', 'Customer'),
        ('DL', 'Deliverer'),
        ('CH', 'Chef'),
        ('MN', 'Manager')], default="CU")

class Employee(Model):
    login       = OneToOneField(User, CASCADE)
    balance     = IntegerField(default=0)
    salary      = IntegerField(default=2000) # cents per hour
    bonus       = IntegerField(default=10000) # fixed amount 
    demotion    = IntegerField(default=1500) # salary when demoted

    def average_rating(self):
        """Calculate average dish rating for this employee (typically a Chef).

        Returns the average of all ratings on dishes created by this employee,
        or None if no ratings exist.
        """
        from django.db.models import Avg
        from .dish import Dish
        from .dish import DishRating

        # Get all dishes created by this employee and their average rating
        avg_rating = DishRating.objects.filter(
            dish__chef__login=self.login
        ).aggregate(avg=Avg('rating'))['avg']

        return avg_rating


    def score(self):
        """Calculate reputation score: (compliments - complaints) with VIP weighting.

        Returns: good + good_vip - bad - bad_vip where:
          good = count of compliments from any user
          good_vip = count of compliments from VIP customers
          bad = count of valid complaints from any user
          bad_vip = count of valid complaints from VIP customers
        """
        from .complaint import Complaint
        from .compliment import Compliment
        from .customer import Customer

        # All compliments (good)
        good = Compliment.objects.filter(to=self.login).count()

        # Valid complaints (bad)
        bad = Complaint.objects.filter(to=self.login, status='v').count()

        # Compliments from VIP customers (good_vip)
        good_vip = Compliment.objects.filter(
            to=self.login,
            sender__customer__vip=True
        ).count()

        # Valid complaints from VIP customers (bad_vip)
        bad_vip = Complaint.objects.filter(
            to=self.login,
            status='v',
            sender__customer__vip=True
        ).count()

        return good + good_vip - bad - bad_vip

