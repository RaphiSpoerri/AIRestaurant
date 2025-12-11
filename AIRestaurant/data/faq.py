
from django.db.models import *
from .users import User

class FAQEntry(Model):
    question = CharField(max_length=300)
    answer = TextField()
    created_at = DateTimeField(auto_now_add=True)
    author = ForeignKey(User, CASCADE, null=True, blank=True, related_name='faq_entries')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Q: {self.question[:50]}"

class ReportedFAQ(Model):
    faq_entry = ForeignKey(FAQEntry, CASCADE)
    reported_by = ForeignKey(User, CASCADE)
    reported_at = DateTimeField(auto_now_add=True)
    status = CharField(max_length=10, choices=[
        ('pending', 'Pending'),
        ('deleted', 'Deleted'),
        ('kept', 'Kept'),
    ], default='pending')

    class Meta:
        ordering = ['-reported_at']

    def __str__(self):
        return f"Report on: {self.faq_entry.question[:50]}"
