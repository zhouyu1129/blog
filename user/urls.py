from django.urls import path
from .views import *

app_name = 'user'

urlpatterns = [
    path('login', login_view, name="login"),
    path('register', register_view, name="register"),
    path('logout', logout_view, name="logout"),
    path('email_verify/<uuid:user_uuid>', email_verify, name="email_verify"),
]