from django.core.management.base import BaseCommand
from AIRestaurant.data.users import User
from AIRestaurant.data.manager import Manager
from AIRestaurant.data.chef import Chef
from AIRestaurant.data.deliverer import Deliverer
from AIRestaurant.data.customer import Customer

class Command(BaseCommand):
    help = 'Populate database with initial data'

    def handle(self, *args, **options):
        CHEFS = [
            ('Mordecai Shafier', 'moko1234'),
            ('Abraham Spoerri', 'raphaelsbrother')
        ]

        DELIVERERS = [
            ('John Doe', 'johndoe'),
            ('Jane Smith', 'janesmith')
        ]

        CUSTOMERS = [
            ('Ploni Almoni', 'plonialmoni'),
            ('Karen Smith', 'karensmith'),
        ]

        # Clear existing data
        for model in [Manager, Chef, Deliverer, Customer, User]:
            model.objects.all().delete()

        raphael_login = User.objects.create_user(
            username='raphael',
            email='raphael@example.com',
            password='!@#$%^&*',
        )
        raphael_login.type = 'MN'
        raphael_login.status = 'AC'
        raphael_login.save()
        raphael = Manager.objects.create(login=raphael_login)
        raphael.save()
        self.stdout.write(self.style.SUCCESS('✓ Created Manager: raphael'))

        for name, password in CHEFS:
            user = User.objects.create_user(
                username=name.lower().replace(' ', ''),
                email=f"{name.lower().replace(' ', '')}@example.com",
                password=password,
            )
            user.type = 'CH'
            user.status = 'AC'
            user.save()
            chef = Chef.objects.create(login=user)
            chef.save()
            self.stdout.write(self.style.SUCCESS(f'✓ Created Chef: {name}'))

        for name, password in DELIVERERS:
            user = User.objects.create_user(
                username=name.lower().replace(' ', ''),
                email=f"{name.lower().replace(' ', '')}@example.com",
                password=password,
            )
            user.type = 'DL'
            user.status = 'AC'
            user.save()
            deliverer = Deliverer.objects.create(login=user)
            deliverer.save()
            self.stdout.write(self.style.SUCCESS(f'✓ Created Deliverer: {name}'))

        for name, password in CUSTOMERS:
            user = User.objects.create_user(
                username=name.lower().replace(' ', ''),
                email=f"{name.lower().replace(' ', '')}@example.com",
                password=password,
            )
            user.type = 'CU'
            user.status = 'AC'
            user.save()
            customer = Customer.objects.create(login=user)
            customer.save()
            self.stdout.write(self.style.SUCCESS(f'✓ Created Customer: {name}'))

        self.stdout.write(self.style.SUCCESS('Database populated successfully!'))
