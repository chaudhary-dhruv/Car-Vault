from django.contrib import admin

from .models import Activity, Car, Conversation, EmailOTP, Message, TestDriveRequest, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    ordering = ["email"]
    list_display = ["email", "full_name", "role", "account_state", "is_staff", "is_admin"]
    list_filter = ["role", "account_state", "is_staff", "is_admin", "gender"]
    search_fields = ["email", "firstname", "lastname"]
    readonly_fields = ["create_at", "updated_at", "otp_verified_at", "last_seen_at"]


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    list_display = ["brand", "model_name", "seller", "listing_status", "fuel_type", "price", "featured"]
    list_filter = ["listing_status", "brand", "body_type", "fuel_type", "featured"]
    search_fields = ["brand", "model_name", "tagline"]
    prepopulated_fields = {"slug": ["brand", "model_name"]}


@admin.register(EmailOTP)
class EmailOTPAdmin(admin.ModelAdmin):
    list_display = ["user", "purpose", "code", "expires_at", "is_used", "created_at"]
    list_filter = ["purpose", "is_used"]
    search_fields = ["user__email", "code"]


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ["car", "buyer", "seller", "status", "proposed_price", "accepted_price", "updated_at"]
    list_filter = ["status"]
    search_fields = ["car__brand", "car__model_name", "buyer__email", "seller__email"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["conversation", "sender", "created_at", "is_read"]
    list_filter = ["is_read"]
    search_fields = ["sender__email", "content"]


@admin.register(TestDriveRequest)
class TestDriveRequestAdmin(admin.ModelAdmin):
    list_display = ["car", "buyer", "seller", "scheduled_for", "status"]
    list_filter = ["status"]
    search_fields = ["car__brand", "car__model_name", "buyer__email", "seller__email"]


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ["user", "title", "activity_type", "status", "due_at"]
    list_filter = ["activity_type", "status"]
    search_fields = ["user__email", "title", "description"]
