from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('blogList/', views.blog_list, name='blog_list'),
    path('blog/<int:blog_id>/<str:lang_code>/', views.blog_detail, name='blog_detail'),
    path('', views.upload_page, name='upload_page'),  # Upload page as home
    path('preview-text/<str:filename>/', views.preview_text, name='preview_text'),  # New preview page
    path('process/', views.process_files, name='process_files'),  # Processing page
    path('translate/<str:lang_code>/', views.translation_result, name='translation_result'),  # For translation results
    path('transcribe/', views.transcription_result, name='transcription_result'),  # For transcription results
]

# Serve media files in development
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)