from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from restaurant.models import Menu, Order, OrderItem

User = get_user_model()


class Command(BaseCommand):
    help = 'Create sample data for the restaurant application'

    def handle(self, *args, **options):
        # Create manager
        manager, created = User.objects.get_or_create(
            username='manager',
            defaults={
                'email': 'manager@restaurant.com',
                'role': 'Manager',
                'is_staff': True,
            }
        )
        if created:
            manager.set_password('manager123')
            manager.save()
            self.stdout.write(self.style.SUCCESS('Created manager account'))

        # Create chef
        chef, created = User.objects.get_or_create(
            username='chef1',
            defaults={
                'email': 'chef1@restaurant.com',
                'role': 'Chef',
                'salary': 5000.0,
            }
        )
        if created:
            chef.set_password('chef1')
            chef.save()
            self.stdout.write(self.style.SUCCESS('Created chef account'))

        # Create delivery person
        delivery, created = User.objects.get_or_create(
            username='delivery1',
            defaults={
                'email': 'delivery1@restaurant.com',
                'role': 'DeliveryPerson',
                'salary': 3000.0,
            }
        )
        if created:
            delivery.set_password('delivery123')
            delivery.save()
            self.stdout.write(self.style.SUCCESS('Created delivery person account'))

        # Create sample menu items
        menu_items_data = [
            {'name': 'Margherita Pizza', 'description': 'Classic pizza with tomato and mozzarella', 
             'price': 12.99, 'category': 'Pizza', 'chef': chef},
            {'name': 'Grilled Chicken', 'description': 'Tender grilled chicken with herbs', 
             'price': 15.99, 'category': 'Main Course', 'chef': chef},
            {'name': 'Caesar Salad', 'description': 'Fresh romaine lettuce with caesar dressing', 
             'price': 8.99, 'category': 'Salad', 'chef': chef},
            {'name': 'Chocolate Cake', 'description': 'Rich chocolate cake with frosting', 
             'price': 6.99, 'category': 'Dessert', 'chef': chef},
            {'name': 'Burger Deluxe', 'description': 'Juicy beef burger with all the fixings', 
             'price': 11.99, 'category': 'Burger', 'chef': chef},
        ]

        for item_data in menu_items_data:
            menu_item, created = Menu.objects.get_or_create(
                name=item_data['name'],
                defaults=item_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created menu item: {item_data["name"]}'))

        self.stdout.write(self.style.SUCCESS('\nSample data created successfully!'))
        self.stdout.write(self.style.SUCCESS('Manager: username=manager, password=manager123'))
        self.stdout.write(self.style.SUCCESS('Chef: username=chef1, password=chef1'))
        self.stdout.write(self.style.SUCCESS('Delivery: username=delivery1, password=delivery123'))

