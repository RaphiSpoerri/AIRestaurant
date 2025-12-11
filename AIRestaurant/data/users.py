

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
    status      = CharField(max_length=2, choices=[
        ('FD', 'Fired'),
        ('OK', 'Okay'),
        ('WR', 'Warned'),
        ('PR', 'Promoted'),
        ('DM', 'Demoted'),
    ], default="OK")

    def average_rating(self):
        """Calculate average dish rating for this employee (typically a Chef).

        Returns the average of all ratings on dishes created by this employee,
        or None if no ratings exist.
        """
        from django.db.models import Avg
        from .chef import Product, ProductRating

        # Get average rating over FOOD products created by this employee.
        # Merch products (type='merch') are excluded so their ratings
        # do not affect staff reputation.
        avg_rating = ProductRating.objects.filter(
            product__type="food",
            product__creator__login=self.login,
        ).aggregate(avg=Avg("rating"))["avg"]

        return avg_rating


    def score(self):
        """Calculate reputation score: (compliments - complaints) with VIP weighting.

        Returns: good + good_vip - bad - bad_vip where:
          good = count of compliments from any user
          good_vip = count of compliments from VIP customers
          bad = count of valid complaints from any user
          bad_vip = count of valid complaints from VIP customers
        """
        from .message import Complaint, Compliment
        from .customer import Customer

        # All compliments (good)
        good = Compliment.objects.filter(to=self.login).count()

        # Valid complaints (bad)
        bad = Complaint.objects.filter(to=self.login, status='v').count()

        # Determine VIP customer user ids
        vip_user_ids = list(
            Customer.objects.filter(vip=True).values_list('login_id', flat=True)
        )

        # Compliments from VIP customers (good_vip)
        good_vip = Compliment.objects.filter(
            to=self.login,
            sender_id__in=vip_user_ids,
        ).count()

        # Valid complaints from VIP customers (bad_vip)
        bad_vip = Complaint.objects.filter(
            to=self.login,
            status='v',
            sender_id__in=vip_user_ids,
        ).count()

        return good + good_vip - bad - bad_vip
    def suspend_for_firing(self):
        """Suspend this employee's account in preparation for firing."""
        self.status = 'FD'
        self.login.status = 'SU'
        self.login.save(update_fields=["status"])
        self.save(update_fields=["status"])

    def add_compliment_sideaffects(self):
        match self.status:
            case 'FD': assert False, "Cannot compliment a fired employee."
            case 'DM':
                if self.score() > -3:
                    self.status = 'WR'
                    self.salary += self.demotion
                    self.save(update_fields=["status", "salary"])
            case 'PR', 'WR':
                pass
            case 'OK':
                if self.score() >= 3:
                    self.status = 'PR'
                    self.salary += self.bonus
                    self.save(update_fields=["status", "salary"])
    # this function must only be called once the manager reviews the complaint
    # and verifies its validity
    def add_complaint_sideaffects(self):
        match self.status:
            case 'FD': assert False, "Cannot complain about a fired employee."
            case 'DM':
                pass # demoted employees are not fired unless regained reputation
            case 'WR':
                if self.score() <= -3:
                    self.suspend_for_firing()
            case 'PR':
                if self.score() < 3:
                    self.status = 'OK'
                    self.salary -= self.bonus
                    self.save(update_fields=["status", "salary"])
            case 'OK':
                if self.score() <= -3:
                    self.status = 'DM'
                    self.salary -= self.demotion
                    self.save(update_fields=["status", "salary"])