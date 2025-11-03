from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Menu, Order, OrderItem, Complaint, Compliment, Rating, 
    Warning, Blacklist, DeliveryBid, KnowledgeBaseEntry, AIResponseRating
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['username', 'email', 'role', 'balance', 'is_active']
    list_filter = ['role', 'is_active']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role', 'balance', 'salary')}),
    )


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'category', 'chef', 'is_available']
    list_filter = ['category', 'is_available']
    search_fields = ['name', 'description']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'status', 'total_amount', 'timestamp']
    list_filter = ['status', 'timestamp']
    readonly_fields = ['timestamp']


admin.site.register(OrderItem)
admin.site.register(Complaint)
admin.site.register(Compliment)
admin.site.register(Rating)
admin.site.register(Warning)
admin.site.register(Blacklist)
admin.site.register(DeliveryBid)
admin.site.register(KnowledgeBaseEntry)
admin.site.register(AIResponseRating)
