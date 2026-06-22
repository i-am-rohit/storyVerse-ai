from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password

BOOTSTRAP_INPUT = {"class": "form-control"}
BOOTSTRAP_CHECK = {"class": "form-check-input"}


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs=BOOTSTRAP_INPUT))

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        widgets = {
            "username": forms.TextInput(attrs={**BOOTSTRAP_INPUT, "class": "form-control auth-input", "placeholder": "Username"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            "username": "Username",
            "email": "Email",
            "password1": "Password",
            "password2": "Confirm password",
        }
        for name, field in self.fields.items():
            field.widget.attrs.update(BOOTSTRAP_INPUT)
            field.widget.attrs["class"] = "form-control auth-input"
            if name in placeholders:
                field.widget.attrs["placeholder"] = placeholders[name]

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class AdminUserCreateForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs=BOOTSTRAP_INPUT),
    )
    password2 = forms.CharField(
        label="Confirm password",
        widget=forms.PasswordInput(attrs=BOOTSTRAP_INPUT),
    )

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "is_staff", "is_active")
        widgets = {
            "username": forms.TextInput(attrs=BOOTSTRAP_INPUT),
            "email": forms.EmailInput(attrs=BOOTSTRAP_INPUT),
            "first_name": forms.TextInput(attrs=BOOTSTRAP_INPUT),
            "last_name": forms.TextInput(attrs=BOOTSTRAP_INPUT),
            "is_staff": forms.CheckboxInput(attrs=BOOTSTRAP_CHECK),
            "is_active": forms.CheckboxInput(attrs=BOOTSTRAP_CHECK),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["is_active"].initial = True

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        validate_password(password2)
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class AdminPasswordResetForm(forms.Form):
    password1 = forms.CharField(
        label="New password",
        widget=forms.PasswordInput(attrs=BOOTSTRAP_INPUT),
    )
    password2 = forms.CharField(
        label="Confirm new password",
        widget=forms.PasswordInput(attrs=BOOTSTRAP_INPUT),
    )

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        if password2:
            validate_password(password2)
        return cleaned
