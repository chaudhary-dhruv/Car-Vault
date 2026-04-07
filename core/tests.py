from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Car, Conversation, EmailOTP, User


class CarVaultWorkflowTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.seller = User.objects.create_user(
            email="seller@example.com",
            password="Seller123!",
            firstname="Seller",
            lastname="One",
            role=User.Role.SELLER,
            account_state=User.AccountState.ACTIVE,
            is_active=True,
        )
        cls.buyer = User.objects.create_user(
            email="buyer@example.com",
            password="Buyer123!",
            firstname="Buyer",
            lastname="One",
            role=User.Role.BUYER,
            account_state=User.AccountState.ACTIVE,
            is_active=True,
        )
        cls.car = Car.objects.create(
            seller=cls.seller,
            brand="Tesla",
            model_name="Model 3",
            tagline="Electric sedan",
            year=2025,
            body_type=Car.BodyType.SEDAN,
            fuel_type=Car.FuelType.ELECTRIC,
            transmission="Single-speed automatic",
            drive_type="RWD",
            listing_status=Car.ListingStatus.ACTIVE,
            price=38990,
            mileage=132,
            horsepower=283,
            torque=420,
            top_speed=125,
            zero_to_sixty=5.8,
            range_km=438,
            battery_capacity=60,
            seating_capacity=5,
            cargo_space=22.9,
            ground_clearance=138,
            safety_rating=4.9,
            warranty_years=4,
            image_url="https://example.com/car1.jpg",
            description="A practical EV.",
            key_features="Feature one,Feature two",
            pros="Pro one\nPro two",
            cons="Con one",
            featured=True,
        )

    def test_home_page_loads(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Find your perfect drive")

    def test_otp_verification_activates_user(self):
        inactive_user = User.objects.create_user(
            email="inactive@example.com",
            password="Inactive123!",
            firstname="Inactive",
            lastname="User",
            role=User.Role.BUYER,
        )
        otp = EmailOTP.objects.create(
            user=inactive_user,
            purpose=EmailOTP.Purpose.ACCOUNT_ACTIVATION,
            code="123456",
            expires_at=timezone.now() + timedelta(minutes=10),
        )
        response = self.client.post(reverse("verify_otp"), {"email": inactive_user.email, "code": otp.code})
        inactive_user.refresh_from_db()
        otp.refresh_from_db()
        self.assertRedirects(response, reverse("login"))
        self.assertEqual(inactive_user.account_state, User.AccountState.ACTIVE)
        self.assertTrue(inactive_user.is_active)
        self.assertTrue(otp.is_used)

    def test_buyer_can_start_conversation(self):
        self.client.force_login(self.buyer)
        response = self.client.post(
            reverse("start_conversation", args=[self.car.slug]),
            {"message": "I want to buy this car.", "proposed_price": "38000"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Conversation.objects.count(), 1)
        conversation = Conversation.objects.first()
        self.assertEqual(conversation.buyer, self.buyer)
        self.assertEqual(conversation.seller, self.seller)

    def test_role_based_dashboard_redirect_for_seller(self):
        self.client.force_login(self.seller)
        response = self.client.get(reverse("dashboard"))
        self.assertRedirects(response, reverse("seller_dashboard"))

    def test_display_image_uses_placeholder_when_image_missing(self):
        self.car.image_url = ""
        self.car.image_file = None
        self.assertEqual(self.car.display_image, "/static/images/car-placeholder.svg")

    def test_google_imgres_url_is_normalized_for_display(self):
        self.car.image_url = (
            "https://www.google.com/imgres?q=sedan%20car&imgurl="
            "https%3A%2F%2Fspn-sta.spinny.com%2Fblog%2F20220228143146%2F559212.jpeg"
        )
        self.assertEqual(
            self.car.display_image,
            "https://spn-sta.spinny.com/blog/20220228143146/559212.jpeg",
        )

    def test_bing_thumbnail_url_falls_back_to_placeholder(self):
        self.car.image_url = "https://tse1.mm.bing.net/th/id/OIP.example?pid=ImgDet"
        self.assertEqual(self.car.display_image, "/static/images/car-placeholder.svg")
