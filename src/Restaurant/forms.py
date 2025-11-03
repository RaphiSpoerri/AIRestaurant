from django import forms
from .models import User, Menu, Order, Complaint, Compliment, Rating, DeliveryBid


class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    password_confirm = forms.CharField(widget=forms.PasswordInput, label='Confirm Password')
    
    class Meta:
        model = User
        fields = ['username', 'email', 'role']
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Passwords don't match")
        
        return cleaned_data


class MenuItemForm(forms.ModelForm):
    class Meta:
        model = Menu
        fields = ['name', 'description', 'price', 'category', 'chef', 'image', 'is_available']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'chef': forms.Select(attrs={'class': 'form-select'}),
        }


class ComplaintForm(forms.ModelForm):
    class Meta:
        model = Complaint
        fields = ['filed_against', 'order', 'type', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'order': forms.Select(attrs={'class': 'form-select'}),
            'filed_against': forms.Select(attrs={'class': 'form-select'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['order'].required = False
        self.fields['filed_against'].required = True


class ComplimentForm(forms.ModelForm):
    class Meta:
        model = Compliment
        fields = ['filed_against', 'order', 'type', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 5}),
            'order': forms.Select(attrs={'class': 'form-select'}),
            'filed_against': forms.Select(attrs={'class': 'form-select'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['order'].required = False
        self.fields['filed_against'].required = True


class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ['chef', 'menu_item', 'rating', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3}),
        }


class DeliveryBidForm(forms.ModelForm):
    class Meta:
        model = DeliveryBid
        fields = ['bid_amount']


class DepositForm(forms.Form):
    amount = forms.FloatField(min_value=0.01, widget=forms.NumberInput(attrs={'step': '0.01'}))

