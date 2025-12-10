
from django.db.models import *
from typing import *
from .users import User, Employee
from .deliverer import OrderedDish
from .chef import Dish

class Customer(Model):
    login       = ForeignKey(User, on_delete=CASCADE)
    warnings    = PositiveIntegerField(default=0)
    balance     = PositiveIntegerField(default=0)  # in cents
    vip         = BooleanField(default=False)

    def complain_about(self, person: Union['Customer', Employee], message: str):
        # TODO: create a Complaint object and save it
        raise NotImplementedError()

    def add_warning(self):
        self.warnings += 1
        if not self.vip:
            if self.warnings == 3:
                # TODO: delete this account. We'll figure out how to do that
                raise NotImplementedError()
        elif self.warnings == 2:
            self.warnings = 0
            self.vip = False
        
        self.save()

    
    def order(self, dishes: List[OrderedDish]):
        """
        TODO:
        I'm not sure about the input format yet, but for now, given a list of OrderedDish,
        add up the cost by calling total_cost() on each.
        
        If that cost is greater than self.balance
        """
        pass

