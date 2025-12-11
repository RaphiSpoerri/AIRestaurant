from django.core.management.base import BaseCommand
from AIRestaurant.data.users import User
from AIRestaurant.data.manager import Manager
from AIRestaurant.data.chef import Chef, Dish
from AIRestaurant.data.deliverer import Deliverer
from AIRestaurant.data.customer import Customer
from subprocess import run as shell_run
class Command(BaseCommand):
    help = 'Populate database with initial data'

    def handle(self, *args, **options):

        shell_run(['python', 'manage.py', 'migrate'])
        shell_run(['python', 'manage.py', 'makemigrations', 'air'])
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
        DISHES = [
            ('Guacamole', 'guacamole.jpg', 399, 'Mordecai Shafier'),
            ('Chicken Salad with Honey Mustard', 'chicken_salad_with_honey_mustard.png', 899, 'Abraham Spoerri'),
        ]

        # Clear existing data
        for model in [Manager, Chef, Deliverer, Customer, User, Dish]:
            model.objects.all().delete()

        raphael_login = User.objects.create_user(
            username='raphael',
            email='coolrustacean@gmail.com',
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

        for dish_name, image_url, price_cents, chef_name in DISHES:
            chef_user = User.objects.get(username=chef_name.lower().replace(' ', ''))
            chef = Chef.objects.get(login=chef_user)
            dish = Dish.objects.create(
                name=dish_name,
                img=image_url,
                price=price_cents,
                chef=chef
            )
            dish.save()
            self.stdout.write(self.style.SUCCESS(f'✓ Created Dish: {dish_name} by {chef_name}'))
        self.stdout.write(self.style.SUCCESS('Database populated successfully!'))
