from django.core.management.base import BaseCommand
from AIRestaurant.data.users import User
from AIRestaurant.data.manager import Manager
from AIRestaurant.data.chef import Chef, Product
from AIRestaurant.data.deliverer import Deliverer
from AIRestaurant.data.customer import Customer
from AIRestaurant.data.faq import FAQEntry
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

        MERCH = [
            ('AI Restaurant 3D Printed Chef Keychain', 'chef-keychain.jpg', 99),
            ('AI Restaurant T-Shirt', 'ai-restaurant-shirt.png', 1999),
            ('AI Restaurant Mug', 'ai-restaurant-mug.png', 2999),
        ]

        FAQ = [
            ('How to place an order?', 'To place an order, add items to your cart and proceed to checkout.', 'karensmith'),
            ('Is this a real restaurant?', 'No, this is a fictional restaurant created for educational purposes.', 'johndoe')
        ]

        # Clear existing data
        for model in [
            Manager,
            Chef,
            Deliverer,
            Customer,
            User,
            Product,
            FAQEntry,
        ]:
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
            dish = Product.objects.create(
                name=dish_name,
                img=image_url,
                price=price_cents,
                type='food',
                creator=chef,
            )
            dish.save()
            self.stdout.write(self.style.SUCCESS(f'✓ Created Product: {dish_name} by {chef_name}'))

        # Create merch products tagged as type='merch' with anonymous creators
        for merch_name, image_url, price_cents in MERCH:
            product = Product.objects.create(
                name=merch_name,
                img=image_url,
                price=price_cents,
                type='merch',
                creator=None,
            )
            product.save()
            self.stdout.write(self.style.SUCCESS(f'✓ Created Merch Product: {merch_name}'))
        for question, answer, asker_username in FAQ:
            asker_user = User.objects.get(username=asker_username)
            faq_entry = FAQEntry.objects.create(
                question=question,
                answer=answer,
                author=asker_user,
            )
            faq_entry.save()
            self.stdout.write(self.style.SUCCESS(f'✓ Created FAQ entry: {question}'))
        self.stdout.write(self.style.SUCCESS('Database populated successfully!'))

        shell_run(['python', 'manage.py', 'migrate'])
        shell_run(['python', 'manage.py', 'makemigrations', 'air'])