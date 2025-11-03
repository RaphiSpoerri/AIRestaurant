from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, role='Customer', **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('role', 'Manager')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('Visitor', 'Visitor'),
        ('Customer', 'Customer'),
        ('VIP', 'VIP'),
        ('Chef', 'Chef'),
        ('DeliveryPerson', 'Delivery Person'),
        ('Manager', 'Manager'),
    ]
    
    username = models.CharField(max_length=80, unique=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='Customer')
    balance = models.FloatField(default=0.0)
    salary = models.FloatField(default=0.0)
    created_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']
    
    def is_vip(self):
        return self.role == 'VIP'
    
    def is_chef(self):
        return self.role == 'Chef'
    
    def is_delivery(self):
        return self.role == 'DeliveryPerson'
    
    def is_manager(self):
        return self.role == 'Manager'
    
    def is_customer(self):
        return self.role in ['Customer', 'VIP']
    
    def __str__(self):
        return self.username


class Menu(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    price = models.FloatField()
    image = models.ImageField(upload_to='menu_images/', blank=True, null=True)
    chef = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                             related_name='menu_items', limit_choices_to={'role': 'Chef'})
    category = models.CharField(max_length=50, blank=True)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    def average_rating(self):
        ratings = self.ratings.all()
        if not ratings:
            return 0.0
        return sum(r.rating for r in ratings) / len(ratings)
    
    def __str__(self):
        return self.name


class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Preparing', 'Preparing'),
        ('Ready', 'Ready'),
        ('Out for Delivery', 'Out for Delivery'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
    ]
    
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders_placed')
    delivery_person = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='orders_delivered', limit_choices_to={'role': 'DeliveryPerson'})
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    total_amount = models.FloatField()
    timestamp = models.DateTimeField(default=timezone.now)
    delivery_address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"Order #{self.id} by {self.customer.username}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name='order_items')
    quantity = models.IntegerField(default=1)
    subtotal = models.FloatField()
    
    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name}"


class Complaint(models.Model):
    TYPE_CHOICES = [
        ('quality', 'Food Quality'),
        ('service', 'Service'),
        ('delivery', 'Delivery'),
        ('behavior', 'Behavior'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    
    filed_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='complaints_filed')
    filed_against = models.ForeignKey(User, on_delete=models.CASCADE, related_name='complaints_received')
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='complaints')
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, blank=True)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    manager_decision = models.CharField(max_length=20, blank=True)
    manager_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Complaint #{self.id} by {self.filed_by.username}"


class Compliment(models.Model):
    TYPE_CHOICES = [
        ('quality', 'Excellent Food Quality'),
        ('service', 'Great Service'),
        ('delivery', 'Fast Delivery'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
    ]
    
    filed_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='compliments_filed')
    filed_against = models.ForeignKey(User, on_delete=models.CASCADE, related_name='compliments_received')
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='compliments')
    type = models.CharField(max_length=50, choices=TYPE_CHOICES, blank=True)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    manager_decision = models.CharField(max_length=20, blank=True)
    manager_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Compliment #{self.id} by {self.filed_by.username}"


class Rating(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='ratings')
    chef = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings_received',
                            limit_choices_to={'role': 'Chef'})
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ratings_given')
    menu_item = models.ForeignKey(Menu, on_delete=models.SET_NULL, null=True, blank=True, related_name='ratings')
    rating = models.IntegerField()  # 1-5
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"{self.rating} stars by {self.customer.username}"


class Warning(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='warnings')
    reason = models.TextField()
    complaint = models.ForeignKey(Complaint, on_delete=models.SET_NULL, null=True, blank=True, related_name='warnings')
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"Warning for {self.user.username}"


class Blacklist(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='blacklist_entry')
    reason = models.TextField()
    date_added = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"Blacklisted: {self.user.username}"


class DeliveryBid(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Accepted', 'Accepted'),
        ('Rejected', 'Rejected'),
    ]
    
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='bids')
    delivery_person = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bids',
                                       limit_choices_to={'role': 'DeliveryPerson'})
    bid_amount = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"Bid by {self.delivery_person.username} for Order #{self.order.id}"


class KnowledgeBaseEntry(models.Model):
    question = models.TextField()
    answer = models.TextField()
    rating = models.FloatField(default=0.0)
    rating_count = models.IntegerField(default=0)
    flagged = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"KB Entry: {self.question[:50]}"


class AIResponseRating(models.Model):
    kb_entry = models.ForeignKey(KnowledgeBaseEntry, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='ratings_list')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    query = models.TextField()
    response = models.TextField()
    rating = models.IntegerField()  # 0-5 stars
    source = models.CharField(max_length=20)  # 'local' or 'llm'
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"AI Rating: {self.rating} stars"
