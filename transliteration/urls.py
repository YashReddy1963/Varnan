from django.urls import path
from . import views

urlpatterns = [
    path('api/transliterate-image/', views.transliterate_image, name='transliterate_image'),
    path('api/transliterate-single/', views.transliterate_single, name='transliterate_single'),
]
