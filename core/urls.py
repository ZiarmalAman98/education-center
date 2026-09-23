from django.urls import path
from . import views
urlpatterns = [
    path('language/', views.set_language, name='set_language'),
    path('', views.home, name='home'), path('welcome/', views.welcome, name='welcome'), path('home/', views.home, name='home_page'), path('about/', views.about, name='about'),
    path('services/', views.services, name='services'), path('news/', views.news_list, name='news_list'),
    path('news/<int:pk>/', views.news_detail, name='news_detail'), path('contact/', views.contact, name='contact'),
    path('accounts/login/', views.EmailLoginView.as_view(), name='login'),
]
