import os
import random
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from user.decorators import role_required

from .india import format_inr
from .forms import (
    ActivityForm,
    CarListingForm,
    ConversationStartForm,
    MessageReplyForm,
    OTPVerificationForm,
    ResendOTPForm,
    TestDriveRequestForm,
    UserLoginForm,
    UserSignupForm,
)
from .models import Activity, Car, Conversation, EmailOTP, Message, TestDriveRequest, User


def create_activity(user, activity_type, title, description="", related_car=None, due_at=None, status=Activity.Status.PENDING):
    return Activity.objects.create(
        user=user,
        activity_type=activity_type,
        title=title,
        description=description,
        related_car=related_car,
        due_at=due_at,
        status=status,
    )


def generate_otp_code():
    return f"{random.randint(0, 999999):06d}"


def send_html_email(subject, to_email, template_name, context, text_content):
    from_email = settings.EMAIL_HOST_USER or "noreply@carvault.local"
    html_content = render_to_string(template_name, context)
    email = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
    email.attach_alternative(html_content, "text/html")
    try:
        email.send()
        return True, None
    except Exception as exc:
        return False, str(exc)


def send_activation_otp(user):
    EmailOTP.objects.filter(user=user, purpose=EmailOTP.Purpose.ACCOUNT_ACTIVATION, is_used=False).update(is_used=True)
    otp = EmailOTP.objects.create(
        user=user,
        purpose=EmailOTP.Purpose.ACCOUNT_ACTIVATION,
        code=generate_otp_code(),
        expires_at=EmailOTP.expiry_time(),
    )
    sent, error_message = send_html_email(
        "Verify your CarVault account",
        user.email,
        "email/account_activation.html",
        {"user": user, "otp": otp},
        f"Hi {user.firstname}, your CarVault verification code is {otp.code}.",
    )
    return otp, sent, error_message


def userSignupView(request):
    form = UserSignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        user.account_state = User.AccountState.INACTIVE
        user.is_active = False
        user.save()
        otp, sent, error_message = send_activation_otp(user)
        if sent:
            messages.success(request, "Your account was created. Check your email for the OTP code.")
        elif settings.DEBUG:
            messages.warning(
                request,
                f"OTP email could not be sent from this machine. Dev OTP: {otp.code}. Error: {error_message}",
            )
        else:
            messages.error(request, "Your account was created, but the OTP email could not be delivered.")
        return redirect(f"{reverse_url('verify_otp')}?email={user.email}")

    return render(request, "core/signUp.html", {"form": form})


def verify_otp_view(request):
    initial_email = request.GET.get("email", "")
    form = OTPVerificationForm(request.POST or None, initial={"email": initial_email})
    resend_form = ResendOTPForm(initial={"email": initial_email})
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        code = form.cleaned_data["code"]
        user = get_object_or_404(User, email=email)
        otp = EmailOTP.objects.filter(
            user=user,
            purpose=EmailOTP.Purpose.ACCOUNT_ACTIVATION,
            code=code,
            is_used=False,
            expires_at__gte=timezone.now(),
        ).first()
        if otp:
            otp.is_used = True
            otp.save(update_fields=["is_used"])
            user.mark_active()
            create_activity(
                user,
                Activity.Type.HISTORY,
                "Account activated",
                "Your email OTP verification was completed successfully.",
                status=Activity.Status.DONE,
            )
            messages.success(request, "Your account is verified. You can log in now.")
            return redirect("login")
        messages.error(request, "The OTP code is invalid or expired.")

    return render(request, "core/verify_otp.html", {"form": form, "resend_form": resend_form})


def resend_otp_view(request):
    form = ResendOTPForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = get_object_or_404(User, email=form.cleaned_data["email"])
        otp, sent, error_message = send_activation_otp(user)
        if sent:
            messages.success(request, "A new OTP code was sent to your email.")
        elif settings.DEBUG:
            messages.warning(
                request,
                f"OTP resend failed on email delivery. Dev OTP: {otp.code}. Error: {error_message}",
            )
        else:
            messages.error(request, "A new OTP was generated, but email delivery failed.")
        return redirect(f"{reverse_url('verify_otp')}?email={user.email}")
    return redirect("signUp")


def userLoginView(request):
    form = UserLoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]
        user = User.objects.filter(email=email).first()
        if user and user.account_state == User.AccountState.INACTIVE:
            messages.error(request, "Verify your email first using the OTP sent at signup.")
            return redirect(f"{reverse_url('verify_otp')}?email={email}")
        if user and user.account_state in [User.AccountState.BLOCKED, User.AccountState.DELETED]:
            return render(request, "core/login.html", {"form": form, "account_error": "This account is unavailable."})

        authenticated_user = authenticate(request, email=email, password=password)
        if authenticated_user:
            login(request, authenticated_user)
            authenticated_user.last_seen_at = timezone.now()
            authenticated_user.save(update_fields=["last_seen_at"])
            return redirect("dashboard")
        return render(request, "core/login.html", {"form": form, "login_error": True})

    return render(request, "core/login.html", {"form": form})


@login_required
def dashboard_redirect(request):
    if request.user.role == User.Role.ADMIN:
        return redirect("admin_dashboard")
    if request.user.role == User.Role.SELLER:
        return redirect("seller_dashboard")
    return redirect("buyer_dashboard")


def home(request):
    featured_cars = Car.objects.filter(featured=True, listing_status=Car.ListingStatus.ACTIVE)[:6]
    brands = Car.objects.filter(listing_status=Car.ListingStatus.ACTIVE).values_list("brand", flat=True).distinct().order_by("brand")[:6]
    comparison_pairs = [
        {"left": "Hyundai Creta", "right": "Kia Seltos"},
        {"left": "BMW i4", "right": "Tesla Model 3"},
        {"left": "BMW X5", "right": "Audi Q7"},
    ]
    return render(
        request,
        "core/home.html",
        {
            "featured_cars": featured_cars,
            "brands": brands,
            "comparison_pairs": comparison_pairs,
            "cars": Car.objects.filter(listing_status=Car.ListingStatus.ACTIVE)[:8],
        },
    )


@role_required([User.Role.BUYER])
def buyer_dashboard(request):
    conversations = Conversation.objects.filter(buyer=request.user).select_related("car", "seller")[:5]
    test_drives = TestDriveRequest.objects.filter(buyer=request.user).select_related("car", "seller")[:5]
    activities = Activity.objects.filter(user=request.user)[:6]
    available_cars = Car.objects.filter(listing_status=Car.ListingStatus.ACTIVE)[:6]
    return render(
        request,
        "core/dashboards/buyer_dashboard.html",
        {
            "conversations": conversations,
            "test_drives": test_drives,
            "activities": activities,
            "available_cars": available_cars,
        },
    )


@role_required([User.Role.SELLER])
def seller_dashboard(request):
    listings = Car.objects.filter(seller=request.user).order_by("-updated_at")
    conversations = Conversation.objects.filter(seller=request.user).select_related("car", "buyer")[:5]
    test_drives = TestDriveRequest.objects.filter(seller=request.user).select_related("car", "buyer")[:5]
    activities = Activity.objects.filter(user=request.user)[:6]
    return render(
        request,
        "core/dashboards/seller_dashboard.html",
        {
            "listings": listings,
            "conversations": conversations,
            "test_drives": test_drives,
            "activities": activities,
        },
    )


@role_required([User.Role.ADMIN])
def admin_dashboard(request):
    context = {
        "buyers_count": User.objects.filter(role=User.Role.BUYER).count(),
        "sellers_count": User.objects.filter(role=User.Role.SELLER).count(),
        "cars_count": Car.objects.count(),
        "pending_listings": Car.objects.filter(listing_status=Car.ListingStatus.PENDING).count(),
        "open_conversations": Conversation.objects.filter(status=Conversation.Status.OPEN).count(),
        "test_drive_requests": TestDriveRequest.objects.count(),
    }
    return render(request, "core/dashboards/admin_dashboard.html", context)


def car_catalog(request):
    cars = Car.objects.filter(listing_status=Car.ListingStatus.ACTIVE)
    search = request.GET.get("search", "").strip()
    brand = request.GET.get("brand", "").strip()
    fuel = request.GET.get("fuel", "").strip()
    body = request.GET.get("body", "").strip()
    sort = request.GET.get("sort", "popularity").strip()

    if search:
        cars = cars.filter(
            Q(brand__icontains=search)
            | Q(model_name__icontains=search)
            | Q(tagline__icontains=search)
            | Q(body_type__icontains=search)
        )
    if brand:
        cars = cars.filter(brand__iexact=brand)
    if fuel:
        cars = cars.filter(fuel_type__iexact=fuel)
    if body:
        cars = cars.filter(body_type__iexact=body)

    sort_map = {
        "price_low": "price",
        "price_high": "-price",
        "fastest": "zero_to_sixty",
        "range": "-range_km",
        "popularity": "-featured",
    }
    cars = cars.order_by(sort_map.get(sort, "-featured"), "brand", "model_name")

    return render(
        request,
        "core/catalog.html",
        {
            "cars": cars,
            "selected_brand": brand,
            "selected_fuel": fuel,
            "selected_body": body,
            "search": search,
            "sort": sort,
            "brands": Car.objects.values_list("brand", flat=True).distinct().order_by("brand"),
            "fuel_types": [choice[0] for choice in Car.FuelType.choices],
            "body_types": [choice[0] for choice in Car.BodyType.choices],
        },
    )


def car_detail(request, slug):
    base_queryset = Car.objects.filter(listing_status=Car.ListingStatus.ACTIVE)
    if request.user.is_authenticated and request.user.role in [User.Role.SELLER, User.Role.ADMIN]:
        base_queryset = Car.objects.all()
    car = get_object_or_404(base_queryset, slug=slug)
    similar_cars = Car.objects.exclude(pk=car.pk).filter(listing_status=Car.ListingStatus.ACTIVE).filter(
        Q(body_type=car.body_type) | Q(fuel_type=car.fuel_type)
    )[:3]
    return render(
        request,
        "core/car_detail.html",
        {
            "car": car,
            "similar_cars": similar_cars,
            "compare_options": Car.objects.filter(listing_status=Car.ListingStatus.ACTIVE).exclude(pk=car.pk),
            "conversation_form": ConversationStartForm(),
            "test_drive_form": TestDriveRequestForm(),
        },
    )


@role_required([User.Role.SELLER])
def seller_listing_create(request):
    form = CarListingForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        car = form.save(commit=False)
        car.seller = request.user
        if not car.listing_status:
            car.listing_status = Car.ListingStatus.PENDING
        car.save()
        create_activity(
            request.user,
            Activity.Type.HISTORY,
            f"Listing created for {car.title}",
            f"Status: {car.get_listing_status_display()}",
            related_car=car,
            status=Activity.Status.DONE,
        )
        messages.success(request, "Car listing saved successfully.")
        return redirect("seller_dashboard")
    return render(request, "core/seller/listing_form.html", {"form": form, "page_title": "Create Listing"})


@role_required([User.Role.SELLER])
def seller_listing_update(request, slug):
    car = get_object_or_404(Car, slug=slug, seller=request.user)
    form = CarListingForm(request.POST or None, request.FILES or None, instance=car)
    if request.method == "POST" and form.is_valid():
        car = form.save()
        create_activity(
            request.user,
            Activity.Type.HISTORY,
            f"Listing updated for {car.title}",
            f"Lifecycle changed to {car.get_listing_status_display()}",
            related_car=car,
            status=Activity.Status.DONE,
        )
        messages.success(request, "Listing updated successfully.")
        return redirect("seller_dashboard")
    return render(request, "core/seller/listing_form.html", {"form": form, "page_title": "Update Listing", "car": car})


@role_required([User.Role.BUYER])
def start_conversation(request, slug):
    car = get_object_or_404(Car, slug=slug, listing_status=Car.ListingStatus.ACTIVE)
    if request.method != "POST":
        return redirect("car_detail", slug=slug)

    form = ConversationStartForm(request.POST)
    if form.is_valid():
        conversation, created = Conversation.objects.get_or_create(
            car=car,
            buyer=request.user,
            seller=car.seller,
            defaults={"proposed_price": form.cleaned_data.get("proposed_price")},
        )
        if form.cleaned_data.get("proposed_price"):
            conversation.proposed_price = form.cleaned_data["proposed_price"]
            conversation.save(update_fields=["proposed_price", "updated_at"])
        Message.objects.create(conversation=conversation, sender=request.user, content=form.cleaned_data["message"])
        create_activity(
            request.user,
            Activity.Type.HISTORY,
            f"Started conversation for {car.title}",
            "You initiated a buyer to seller conversation.",
            related_car=car,
            status=Activity.Status.DONE,
        )
        if car.seller:
            create_activity(
                car.seller,
                Activity.Type.TODO,
                f"Respond to buyer for {car.title}",
                f"Conversation with {request.user.full_name or request.user.email}.",
                related_car=car,
            )
        messages.success(request, "Your message was sent to the seller.")
        return redirect("conversation_detail", conversation_id=conversation.id)

    messages.error(request, "Please enter a message to contact the seller.")
    return redirect("car_detail", slug=slug)


@login_required
def conversation_list(request):
    if request.user.role == User.Role.SELLER:
        conversations = Conversation.objects.filter(seller=request.user).select_related("car", "buyer")
    elif request.user.role == User.Role.BUYER:
        conversations = Conversation.objects.filter(buyer=request.user).select_related("car", "seller")
    else:
        conversations = Conversation.objects.all().select_related("car", "buyer", "seller")
    return render(request, "core/messages/conversation_list.html", {"conversations": conversations})


@login_required
def conversation_detail(request, conversation_id):
    conversation = get_object_or_404(Conversation.objects.select_related("car", "buyer", "seller"), pk=conversation_id)
    if request.user not in [conversation.buyer, conversation.seller] and request.user.role != User.Role.ADMIN:
        messages.error(request, "You cannot access this conversation.")
        return redirect("dashboard")

    conversation.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

    form = MessageReplyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        message = form.save(commit=False)
        message.conversation = conversation
        message.sender = request.user
        message.save()
        conversation.updated_at = timezone.now()
        conversation.save(update_fields=["updated_at"])
        create_activity(
            request.user,
            Activity.Type.HISTORY,
            f"Sent message for {conversation.car.title}",
            "Conversation updated.",
            related_car=conversation.car,
            status=Activity.Status.DONE,
        )
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"ok": True})
        return redirect("conversation_detail", conversation_id=conversation.id)

    return render(
        request,
        "core/messages/conversation_detail.html",
        {"conversation": conversation, "form": form},
    )


@login_required
def conversation_messages_fragment(request, conversation_id):
    conversation = get_object_or_404(Conversation.objects.select_related("car", "buyer", "seller"), pk=conversation_id)
    if request.user not in [conversation.buyer, conversation.seller] and request.user.role != User.Role.ADMIN:
        return JsonResponse({"ok": False}, status=403)

    conversation.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
    html = render_to_string(
        "core/messages/_conversation_messages.html",
        {"conversation": conversation, "request": request},
    )
    return JsonResponse({"ok": True, "html": html})


@role_required([User.Role.SELLER])
def update_conversation_status(request, conversation_id, action):
    conversation = get_object_or_404(Conversation, pk=conversation_id, seller=request.user)
    if action == "accept":
        conversation.status = Conversation.Status.DEAL_ACCEPTED
        conversation.accepted_price = conversation.proposed_price or conversation.car.price
        conversation.car.listing_status = Car.ListingStatus.SOLD
        conversation.car.save(update_fields=["listing_status", "updated_at"])
        conversation.save(update_fields=["status", "accepted_price", "updated_at"])
        create_activity(
            request.user,
            Activity.Type.HISTORY,
            f"Deal accepted for {conversation.car.title}",
            f"Accepted price: {conversation.accepted_price}",
            related_car=conversation.car,
            status=Activity.Status.DONE,
        )
        create_activity(
            conversation.buyer,
            Activity.Type.HISTORY,
            f"Deal accepted for {conversation.car.title}",
            "The seller accepted your deal.",
            related_car=conversation.car,
            status=Activity.Status.DONE,
        )
        messages.success(request, "Deal accepted and listing marked as sold.")
    elif action == "decline":
        conversation.status = Conversation.Status.DEAL_DECLINED
        conversation.save(update_fields=["status", "updated_at"])
        messages.info(request, "Deal offer declined.")
    return redirect("conversation_detail", conversation_id=conversation.id)


@role_required([User.Role.BUYER])
def schedule_test_drive(request, slug):
    car = get_object_or_404(Car, slug=slug, listing_status=Car.ListingStatus.ACTIVE)
    form = TestDriveRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        test_drive = form.save(commit=False)
        test_drive.car = car
        test_drive.buyer = request.user
        test_drive.seller = car.seller
        test_drive.save()
        create_activity(
            request.user,
            Activity.Type.MEETING,
            f"Test drive requested for {car.title}",
            test_drive.location,
            related_car=car,
            due_at=test_drive.scheduled_for,
        )
        if car.seller:
            create_activity(
                car.seller,
                Activity.Type.MEETING,
                f"Confirm test drive for {car.title}",
                f"Buyer: {request.user.full_name or request.user.email}",
                related_car=car,
                due_at=test_drive.scheduled_for,
            )
        messages.success(request, "Test drive request created successfully.")
        return redirect("buyer_dashboard")
    messages.error(request, "Please submit a valid test drive request.")
    return redirect("car_detail", slug=slug)


@role_required([User.Role.SELLER, User.Role.ADMIN])
def update_test_drive_status(request, test_drive_id, status):
    queryset = TestDriveRequest.objects.all()
    if request.user.role == User.Role.SELLER:
        queryset = queryset.filter(seller=request.user)
    test_drive = get_object_or_404(queryset, pk=test_drive_id)
    allowed = {choice[0] for choice in TestDriveRequest.Status.choices}
    if status in allowed:
        test_drive.status = status
        test_drive.save(update_fields=["status", "updated_at"])
        messages.success(request, "Test drive status updated.")
    return redirect("seller_dashboard" if request.user.role == User.Role.SELLER else "admin_dashboard")


@login_required
def activity_create(request):
    form = ActivityForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        activity = form.save(commit=False)
        activity.user = request.user
        activity.save()
        messages.success(request, "Activity saved successfully.")
        return redirect("dashboard")
    return render(request, "core/activity_form.html", {"form": form})


def compare_cars(request):
    cars = Car.objects.filter(listing_status=Car.ListingStatus.ACTIVE)
    left = None
    right = None

    car_1_id = request.GET.get("car1")
    car_2_id = request.GET.get("car2")
    if car_1_id and car_2_id:
        left = get_object_or_404(cars, pk=car_1_id)
        right = get_object_or_404(cars, pk=car_2_id)
        if left.pk == right.pk:
            right = None

    comparison_rows = []
    verdict = None
    if left and right:
        comparison_rows = build_comparison_rows(left, right)
        verdict = build_verdict(left, right, comparison_rows)

    return render(
        request,
        "core/compare.html",
        {
            "cars": cars,
            "left": left,
            "right": right,
            "comparison_rows": comparison_rows,
            "verdict": verdict,
        },
    )


def build_comparison_rows(left, right):
    sections = [
        ("Price & Overview", "payments", [("Ex-Showroom Price", "price", "currency_inr", "lower"), ("Drive Type", "drive_type", "text", None), ("Fuel Type", "fuel_type", "text", None), ("Body Type", "body_type", "text", None), ("Listing Status", "listing_status", "text", None)]),
        ("Performance", "speed", [("0-100 km/h", "zero_to_sixty", "seconds_0100", "lower"), ("Horsepower", "horsepower", "hp", "higher"), ("Torque", "torque", "nm", "higher"), ("Top Speed", "top_speed", "kmph", "higher")]),
        ("Range & Efficiency", "ev_station", [("Range", "range_km", "km", "higher"), ("Mileage", "mileage", "kmpl", "higher"), ("Battery/Capacity", "battery_capacity", "kWh", "higher"), ("Warranty", "warranty_years", "years", "higher")]),
        ("Dimensions", "straighten", [("Seats", "seating_capacity", "seats", "higher"), ("Cargo Space", "cargo_space", "liters", "higher"), ("Ground Clearance", "ground_clearance", "mm", "higher")]),
        ("Safety & Tech", "health_and_safety", [("Safety Rating", "safety_rating", "stars", "higher"), ("Transmission", "transmission", "text", None)]),
    ]

    comparison_rows = []
    for section_title, icon, rows in sections:
        section_rows = []
        for label, field, unit, winner_rule in rows:
            left_value = getattr(left, field)
            right_value = getattr(right, field)
            winner = determine_winner(left_value, right_value, winner_rule)
            section_rows.append({"label": label, "left": format_value(left_value, unit), "right": format_value(right_value, unit), "winner": winner})
        comparison_rows.append({"title": section_title, "icon": icon, "rows": section_rows})
    return comparison_rows


def determine_winner(left_value, right_value, rule):
    if rule is None or left_value == right_value:
        return None
    if rule == "higher":
        return "left" if left_value > right_value else "right"
    if rule == "lower":
        return "left" if left_value < right_value else "right"
    return None


def format_value(value, unit):
    if unit == "currency_inr":
        return format_inr(Decimal(value) * Decimal("83"))
    if unit == "seconds":
        return f"{value}s"
    if unit == "seconds_0100":
        return f"{(Decimal(value) * Decimal('1.0356')):.1f}s"
    if unit == "hp":
        return f"{value} bhp"
    if unit == "nm":
        return f"{value} Nm"
    if unit == "kmph":
        return f"{(Decimal(value) * Decimal('1.60934')):.0f} km/h"
    if unit == "km":
        return f"{value} km"
    if unit == "kmpl":
        return f"{(Decimal(value) * Decimal('0.425144')):.1f} km/l"
    if unit == "kWh":
        return f"{value} kWh"
    if unit == "years":
        return f"{value} years"
    if unit == "seats":
        return f"{value} seats"
    if unit == "liters":
        return f"{(Decimal(value) * Decimal('28.3168')):.0f} L"
    if unit == "mm":
        return f"{value} mm"
    if unit == "stars":
        return f"{value} / 5"
    return str(value).replace("_", " ").title()


def build_verdict(left, right, comparison_rows):
    left_score = 0
    right_score = 0
    for section in comparison_rows:
        for row in section["rows"]:
            if row["winner"] == "left":
                left_score += 1
            elif row["winner"] == "right":
                right_score += 1

    winner = left if left_score >= right_score else right
    score = max(left_score, right_score)
    rating = Decimal("7.5") + Decimal(score) / Decimal("4")
    rating = min(rating, Decimal("9.8"))

    return {
        "winner": winner,
        "left_score": left_score,
        "right_score": right_score,
        "rating": f"{rating:.1f}",
        "summary": f"{winner.title} comes out ahead in more measurable categories, making it the stronger trust-first choice for buyers who want a confident comparison.",
    }


def tempFile(request):
    return render(request, "core/temp.html")


def TryHTML(request):
    return render(request, "core/try_html.html")


def reverse_url(name):
    from django.urls import reverse

    return reverse(name)
