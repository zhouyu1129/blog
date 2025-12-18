from .views import *
from django.urls import path

app_name = 'article'

urlpatterns = [
    path('', article_list, name='article_list'),
    path('create/', article_create, name='article_create'),
    path('<int:pk>/', article_detail, name='article_detail'),
]
