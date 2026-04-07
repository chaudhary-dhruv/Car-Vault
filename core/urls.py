from django.contrib.auth import views as auth_views
from django.urls import path

from .forms import CarVaultPasswordResetForm
from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard_redirect, name="dashboard"),
    path("dashboard/buyer/", views.buyer_dashboard, name="buyer_dashboard"),
    path("dashboard/seller/", views.seller_dashboard, name="seller_dashboard"),
    path("dashboard/admin/", views.admin_dashboard, name="admin_dashboard"),
    path("cars/", views.car_catalog, name="car_catalog"),
    path("cars/<slug:slug>/", views.car_detail, name="car_detail"),
    path("seller/listings/new/", views.seller_listing_create, name="seller_listing_create"),
    path("seller/listings/<slug:slug>/edit/", views.seller_listing_update, name="seller_listing_update"),
    path("cars/<slug:slug>/contact/", views.start_conversation, name="start_conversation"),
    path("cars/<slug:slug>/test-drive/", views.schedule_test_drive, name="schedule_test_drive"),
    path("messages/", views.conversation_list, name="conversation_list"),
    path("messages/<int:conversation_id>/", views.conversation_detail, name="conversation_detail"),
    path("messages/<int:conversation_id>/fragment/", views.conversation_messages_fragment, name="conversation_messages_fragment"),
    path("messages/<int:conversation_id>/<str:action>/", views.update_conversation_status, name="update_conversation_status"),
    path("test-drives/<int:test_drive_id>/<str:status>/", views.update_test_drive_status, name="update_test_drive_status"),
    path("activities/new/", views.activity_create, name="activity_create"),
    path("compare/", views.compare_cars, name="compare_cars"),
    path("signUp/", views.userSignupView, name="signUp"),
    path("verify-otp/", views.verify_otp_view, name="verify_otp"),
    path("resend-otp/", views.resend_otp_view, name="resend_otp"),
    path("login/", views.userLoginView, name="login"),
    path(
        "password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="registration/password_reset_form.html",
            email_template_name="registration/password_reset_email.txt",
            html_email_template_name="registration/password_reset_email.html",
            subject_template_name="registration/password_reset_subject.txt",
            form_class=CarVaultPasswordResetForm,
        ),
        name="password_reset",
    ),
    path(
        "password-reset/done/",
        auth_views.PasswordResetDoneView.as_view(template_name="registration/password_reset_done.html"),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(template_name="registration/password_reset_confirm.html"),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(template_name="registration/password_reset_complete.html"),
        name="password_reset_complete",
    ),
    path("temp/", views.tempFile, name="temp"),
    path("try/", views.TryHTML, name="try_html"),
]
