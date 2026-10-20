from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Comment, LostAndFoundItem


class LostFoundForm(forms.ModelForm):
    """Form for creating and updating a lost item report."""

    CATEGORY_CHOICES = [
        ('Electronics', 'Electronics'),
        ('Personal', 'Personal'),
        ('Accessories', 'Accessories'),
        ('Clothing', 'Clothing'),
        ('Books', 'Books'),
        ('Documents', 'Documents'),
        ('Keys', 'Keys'),
        ('Other', 'Other'),
    ]

    category = forms.ChoiceField(
        choices=CATEGORY_CHOICES,
        label='Category',
        initial='Electronics',
    )
    other_category = forms.CharField(
        max_length=100,
        required=False,
        label='Your category',
        widget=forms.TextInput(attrs={'placeholder': 'Type a category'}),
    )

    class Meta:
        model = LostAndFoundItem
        fields = [
            'item_name',
            'category',
            'date_lost_found',
            'location',
            'description',
            'image',
        ]
        widgets = {
            'item_name': forms.TextInput(attrs={'placeholder': 'Item name'}),
            'date_lost_found': forms.DateInput(attrs={'type': 'date'}),
            'location': forms.TextInput(attrs={'placeholder': 'Last known location'}),
            'description': forms.Textarea(
                attrs={'placeholder': 'Add details that may help identify the item.', 'rows': 6}
            ),
            'image': forms.ClearableFileInput(attrs={'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        current_category = getattr(self.instance, 'category', '')

        if current_category and current_category not in dict(self.CATEGORY_CHOICES):
            self.initial['category'] = 'Other'
            self.initial['other_category'] = current_category

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')

        if category == 'Other':
            other_category = cleaned_data.get('other_category', '').strip()
            if not other_category:
                self.add_error('other_category', 'Enter the category for this item.')
            else:
                cleaned_data['category'] = other_category

        return cleaned_data

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Choose an image smaller than 5 MB.')
        return image

    def save(self, commit=True):
        item = super().save(commit=False)
        item.category = self.cleaned_data['category']
        if commit:
            item.save()
            self.save_m2m()
        return item

class CommentForm(forms.ModelForm):
    """Form for responding to a lost item report."""

    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(
                attrs={'placeholder': 'Share where you saw the item or ask a question.', 'rows': 4}
            ),
        }


class RegistrationForm(UserCreationForm):
    """Basic account registration form."""

    pass


class ProfileForm(forms.ModelForm):
    """Form for editing basic account information."""

    class Meta:
        model = get_user_model()
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'autocomplete': 'username'}),
            'first_name': forms.TextInput(attrs={'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email address'}),
        }
