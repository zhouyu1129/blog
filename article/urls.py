from .views import *
from django.urls import path

app_name = 'article'

urlpatterns = [
    path('', article_list, name='article_list'),
    path('create/', article_create, name='article_create'),
    path('<int:index_id>/', article_detail, name='article_detail'),
    path('<int:index_id>/edit/', article_update, name='article_update'),
    path('<int:index_id>/delete/', article_delete, name='article_delete'),
    path('upload-file/', upload_file, name='upload_file'),
    path('delete-temp-file/<uuid:file_id>/', delete_temp_file, name='delete_temp_file'),
    path('get-temp-files/', get_temp_files, name='get_temp_files'),
]
