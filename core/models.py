from datetime import timedelta
from urllib.parse import parse_qs, unquote, urlparse

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from .india import cuft_to_liters, format_inr, mpg_to_kmpl, mph_to_kmph, usd_to_inr, zero_to_hundred_time


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        extra_fields.setdefault("account_state", User.AccountState.INACTIVE)
        extra_fields.setdefault("is_active", False)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        extra_fields.setdefault("account_state", User.AccountState.ACTIVE)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_admin", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_admin") is not True:
            raise ValueError("Superuser must have is_admin=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        BUYER = "buyer", "Buyer"
        SELLER = "seller", "Seller"

    class AccountState(models.TextChoices):
        INACTIVE = "inactive", "Inactive"
        ACTIVE = "active", "Active"
        BLOCKED = "blocked", "Blocked"
        DELETED = "deleted", "Deleted"

    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"

    firstname = models.CharField(max_length=100)
    lastname = models.CharField(max_length=100)
    phone = models.CharField(max_length=15, null=True, blank=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.BUYER)
    account_state = models.CharField(max_length=20, choices=AccountState.choices, default=AccountState.INACTIVE)
    gender = models.CharField(max_length=20, choices=Gender.choices, default=Gender.OTHER)
    otp_verified_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    create_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.firstname} {self.lastname}".strip()

    @property
    def is_buyer(self):
        return self.role == self.Role.BUYER

    @property
    def is_seller(self):
        return self.role == self.Role.SELLER

    def mark_active(self):
        self.account_state = self.AccountState.ACTIVE
        self.is_active = True
        self.otp_verified_at = timezone.now()
        self.save(update_fields=["account_state", "is_active", "otp_verified_at", "updated_at"])


class EmailOTP(models.Model):
    class Purpose(models.TextChoices):
        ACCOUNT_ACTIVATION = "account_activation", "Account Activation"
        PASSWORD_RESET = "password_reset", "Password Reset"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="otps")
    purpose = models.CharField(max_length=30, choices=Purpose.choices)
    code = models.CharField(max_length=6)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.purpose}"

    @property
    def is_valid(self):
        return (not self.is_used) and self.expires_at >= timezone.now()

    @classmethod
    def expiry_time(cls):
        return timezone.now() + timedelta(minutes=10)


class Car(models.Model):
    class BodyType(models.TextChoices):
        SUV = "SUV", "SUV"
        SEDAN = "Sedan", "Sedan"
        HATCHBACK = "Hatchback", "Hatchback"
        COUPE = "Coupe", "Coupe"
        PICKUP = "Pickup", "Pickup"

    class FuelType(models.TextChoices):
        PETROL = "Petrol", "Petrol"
        DIESEL = "Diesel", "Diesel"
        ELECTRIC = "Electric", "Electric"
        HYBRID = "Hybrid", "Hybrid"

    class ListingStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        PENDING = "pending", "Pending"
        SOLD = "sold", "Sold"
        WITHDRAWN = "withdrawn", "Withdrawn"

    seller = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name="listed_cars",
        null=True,
        blank=True,
        limit_choices_to={"role": User.Role.SELLER},
    )
    brand = models.CharField(max_length=100)
    model_name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    tagline = models.CharField(max_length=160)
    year = models.PositiveIntegerField(default=2025)
    body_type = models.CharField(max_length=20, choices=BodyType.choices)
    fuel_type = models.CharField(max_length=20, choices=FuelType.choices)
    transmission = models.CharField(max_length=50)
    drive_type = models.CharField(max_length=50)
    listing_status = models.CharField(max_length=20, choices=ListingStatus.choices, default=ListingStatus.PENDING)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    mileage = models.PositiveIntegerField(help_text="Mileage in MPG or equivalent")
    horsepower = models.PositiveIntegerField()
    torque = models.PositiveIntegerField(help_text="Torque in Nm")
    top_speed = models.PositiveIntegerField(help_text="Top speed in mph")
    zero_to_sixty = models.DecimalField(max_digits=4, decimal_places=1, help_text="0-60 mph time in seconds")
    range_km = models.PositiveIntegerField(help_text="Range in km")
    battery_capacity = models.PositiveIntegerField(help_text="Battery or fuel system capacity")
    seating_capacity = models.PositiveIntegerField(default=5)
    cargo_space = models.DecimalField(max_digits=5, decimal_places=1, help_text="Cargo space in cubic feet")
    ground_clearance = models.PositiveIntegerField(help_text="Ground clearance in mm")
    safety_rating = models.DecimalField(max_digits=2, decimal_places=1)
    warranty_years = models.PositiveIntegerField(default=3)
    image_url = models.URLField(blank=True)
    image_file = models.FileField(upload_to="cars/", blank=True, null=True)
    description = models.TextField()
    key_features = models.TextField(help_text="Comma-separated features")
    pros = models.TextField(help_text="One point per line")
    cons = models.TextField(help_text="One point per line")
    featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["brand", "model_name"]

    def __str__(self):
        return f"{self.brand} {self.model_name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(f"{self.brand}-{self.model_name}")
            slug = base_slug
            counter = 1
            while Car.objects.exclude(pk=self.pk).filter(slug=slug).exists():
                counter += 1
                slug = f"{base_slug}-{counter}"
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def title(self):
        return f"{self.brand} {self.model_name}"

    @property
    def features_list(self):
        return [feature.strip() for feature in self.key_features.split(",") if feature.strip()]

    @property
    def pros_list(self):
        return [item.strip() for item in self.pros.splitlines() if item.strip()]

    @property
    def cons_list(self):
        return [item.strip() for item in self.cons.splitlines() if item.strip()]

    @property
    def is_public(self):
        return self.listing_status == self.ListingStatus.ACTIVE

    @staticmethod
    def normalize_image_url(value):
        image_url = (value or "").strip()
        if not image_url:
            return ""

        parsed = urlparse(image_url)
        if parsed.netloc.lower() in {"google.com", "www.google.com"} and parsed.path == "/imgres":
            query = parse_qs(parsed.query)
            for key in ("imgurl", "mediaurl", "url"):
                candidate = query.get(key, [""])[0].strip()
                if candidate:
                    return unquote(candidate)
        return image_url

    @classmethod
    def is_supported_image_url(cls, value):
        image_url = cls.normalize_image_url(value)
        if not image_url:
            return False

        parsed = urlparse(image_url)
        host = parsed.netloc.lower()
        if parsed.scheme not in {"http", "https"} or not host:
            return False

        if host in {"google.com", "www.google.com", "bing.com", "www.bing.com"}:
            return False

        if host.endswith(".bing.net"):
            return False

        return True

    @property
    def placeholder_image(self):
        return f"{settings.STATIC_URL}images/car-placeholder.svg"

    @property
    def display_image(self):
        if self.image_file:
            try:
                return self.image_file.url
            except ValueError:
                pass

        image_url = self.normalize_image_url(self.image_url)
        if self.is_supported_image_url(image_url):
            return image_url
        return self.placeholder_image

    @property
    def price_inr(self):
        return usd_to_inr(self.price)

    @property
    def formatted_price_inr(self):
        return format_inr(self.price_inr)

    @property
    def mileage_kmpl(self):
        return mpg_to_kmpl(self.mileage)

    @property
    def top_speed_kmph(self):
        return mph_to_kmph(self.top_speed)

    @property
    def zero_to_hundred(self):
        return zero_to_hundred_time(self.zero_to_sixty)

    @property
    def cargo_liters(self):
        return cuft_to_liters(self.cargo_space)


class Conversation(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        DEAL_ACCEPTED = "deal_accepted", "Deal Accepted"
        DEAL_DECLINED = "deal_declined", "Deal Declined"
        CLOSED = "closed", "Closed"

    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name="conversations")
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="buyer_conversations")
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="seller_conversations")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    proposed_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    accepted_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        unique_together = ("car", "buyer", "seller")

    def __str__(self):
        return f"{self.car.title}: {self.buyer.email} -> {self.seller.email}"


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_messages")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Message by {self.sender.email}"


class TestDriveRequest(models.Model):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        CONFIRMED = "confirmed", "Confirmed"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name="test_drives")
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="buyer_test_drives")
    seller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="seller_test_drives")
    scheduled_for = models.DateTimeField()
    location = models.CharField(max_length=255)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["scheduled_for"]

    def __str__(self):
        return f"{self.car.title} test drive for {self.buyer.email}"


class Activity(models.Model):
    class Type(models.TextChoices):
        TODO = "todo", "To-do"
        MEETING = "meeting", "Meeting"
        HISTORY = "history", "History"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        DONE = "done", "Done"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activities")
    activity_type = models.CharField(max_length=20, choices=Type.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    related_car = models.ForeignKey(Car, on_delete=models.SET_NULL, null=True, blank=True, related_name="activities")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["status", "due_at", "-created_at"]

    def __str__(self):
        return f"{self.user.email}: {self.title}"
