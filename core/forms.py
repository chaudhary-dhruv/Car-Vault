from django import forms
from django.contrib.auth.forms import PasswordResetForm, UserCreationForm

from .india import CUFT_TO_LITERS, MPG_TO_KMPL, MPH_TO_KMPH, USD_TO_INR, ZERO_TO_SIXTY_TO_ZERO_TO_HUNDRED
from .models import Activity, Car, Message, TestDriveRequest, User


def add_form_control_styles(form):
    for field in form.fields.values():
        existing = field.widget.attrs.get("class", "")
        field.widget.attrs["class"] = (
            existing
            + " w-full rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-900 focus:border-primary focus:ring-primary"
        ).strip()
    return form


class UserSignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["firstname", "lastname", "gender", "email", "role", "phone"]
        widgets = {"gender": forms.RadioSelect()}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["role"].choices = [
            (User.Role.BUYER, "Buyer"),
            (User.Role.SELLER, "Seller"),
        ]
        add_form_control_styles(self)


class UserLoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_form_control_styles(self)


class OTPVerificationForm(forms.Form):
    email = forms.EmailField(widget=forms.HiddenInput())
    code = forms.CharField(max_length=6, min_length=6)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_form_control_styles(self)


class ResendOTPForm(forms.Form):
    email = forms.EmailField(widget=forms.HiddenInput())


class CarListingForm(forms.ModelForm):
    class Meta:
        model = Car
        exclude = ["seller", "slug", "created_at", "updated_at"]
        widgets = {
            "image_file": forms.ClearableFileInput(attrs={"accept": "image/*"}),
            "description": forms.Textarea(attrs={"rows": 4}),
            "pros": forms.Textarea(attrs={"rows": 3}),
            "cons": forms.Textarea(attrs={"rows": 3}),
            "key_features": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["image_url"].required = False
        self.fields["image_url"].help_text = "Optional. You can leave this empty and upload a local image below."
        self.fields["image_file"].required = False
        self.fields["image_file"].help_text = "Recommended: upload a local car image for better quality."
        self.fields["price"].label = "Price (INR)"
        self.fields["mileage"].label = "Mileage (km/l)"
        self.fields["top_speed"].label = "Top Speed (km/h)"
        self.fields["zero_to_sixty"].label = "0-100 km/h (seconds)"
        self.fields["cargo_space"].label = "Cargo Space (liters)"
        add_form_control_styles(self)

    def clean_price(self):
        return self.cleaned_data["price"] / USD_TO_INR

    def clean_image_url(self):
        image_url = Car.normalize_image_url(self.cleaned_data.get("image_url"))
        if image_url and not Car.is_supported_image_url(image_url):
            raise forms.ValidationError("Use a direct image URL or upload a local image file.")
        return image_url

    def clean(self):
        cleaned_data = super().clean()
        image_url = cleaned_data.get("image_url")
        image_file = cleaned_data.get("image_file")
        if not image_url and not image_file:
            raise forms.ValidationError("Add a car image by upload or direct image URL.")
        return cleaned_data

    def clean_mileage(self):
        return int(round(self.cleaned_data["mileage"] / MPG_TO_KMPL))

    def clean_top_speed(self):
        return int(round(self.cleaned_data["top_speed"] / MPH_TO_KMPH))

    def clean_zero_to_sixty(self):
        return self.cleaned_data["zero_to_sixty"] / ZERO_TO_SIXTY_TO_ZERO_TO_HUNDRED

    def clean_cargo_space(self):
        return self.cleaned_data["cargo_space"] / CUFT_TO_LITERS


class ConversationStartForm(forms.Form):
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}))
    proposed_price = forms.DecimalField(max_digits=10, decimal_places=2, required=False)


class MessageReplyForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ["content"]
        widgets = {"content": forms.Textarea(attrs={"rows": 3, "placeholder": "Type your message..."})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_form_control_styles(self)


class TestDriveRequestForm(forms.ModelForm):
    class Meta:
        model = TestDriveRequest
        fields = ["scheduled_for", "location", "notes"]
        widgets = {
            "scheduled_for": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["scheduled_for"].input_formats = ["%Y-%m-%dT%H:%M"]
        add_form_control_styles(self)


class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ["activity_type", "status", "title", "description", "due_at", "related_car"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "due_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["due_at"].input_formats = ["%Y-%m-%dT%H:%M"]
        if user is not None:
            self.fields["related_car"].queryset = Car.objects.filter(seller=user) | Car.objects.filter(listing_status=Car.ListingStatus.ACTIVE)
        add_form_control_styles(self)


class CarVaultPasswordResetForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        add_form_control_styles(self)
