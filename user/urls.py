from django.urls import path
from .views import *

app_name = 'user'

urlpatterns = [
    path('login', login_view, name="login"),
    path('register', register_view, name="register"),
    path('logout', logout_view, name="logout"),
    path('email_verify/<uuid:user_uuid>/<str:user_email_hash>', email_verify, name="email_verify"),
    path('profile', profile_view, name="profile"),
    path('profile/edit', edit_profile_view, name="edit_profile"),
    path('profile/change_email', change_email_view, name="change_email"),
    path('profile/change_password', change_password_view, name="change_password"),
    path('profile/send_email_code', send_email_code_view, name="send_email_code"),
    path('forgot_password', forgot_password_view, name="forgot_password"),
    path('reset_password/<uuid:user_uuid>/<str:reset_hash>', reset_password_view, name="reset_password"),
]
