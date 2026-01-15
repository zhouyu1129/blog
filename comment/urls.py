from .views import *
from django.urls import path

app_name = 'comment'

urlpatterns = [
    path('<int:article_index_id>/<int:page>/', comment_list, name='comment_list'),
    path('<int:article_index_id>/', comment_list, {'page': 1}, name='comment_list'),
    path('<int:article_index_id>/create/', comment_create, name='comment_create'),
    path('update/<int:comment_index_id>/', comment_update, name='comment_update'),
    path('delete/<int:comment_index_id>/', comment_delete, name='comment_delete'),
]
