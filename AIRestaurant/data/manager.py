
from django.db.models import *
from .users import User

class Manager(Model):
    login = OneToOneField(User, CASCADE)

    def registration_requests(self):
        return User.objects.filter(status='PN')
    
    def approve_registration(self, user: User):
        user.status = 'AC'
        user.id = User.objects.count() + 1
        user.save()

        if user.type == 'CU':
            Customer.objects.create(login=user)
            return redirect('customer')
        if user.type == 'CH':
            Chef.objects.create(login=user)
            return redirect('chef')
        if user.type == 'DL':
            Deliverer.objects.create(login=user)
            return redirect('deliverer')
        if user.type == 'MN':
            Manager.objects.create(login=new_user)
            return redirect('manager')