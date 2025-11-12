
# In your app's apps.py
from django.apps import AppConfig

class AIRestaurantConfig(AppConfig):
    name = 'AIRestaurant'
    label = 'ai-r'

    def ready(self):
        pass