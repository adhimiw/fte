from django.urls import path
from django.views.generic import RedirectView
from django.contrib.auth.views import LogoutView as DjangoLogoutView
from . import views

app_name = 'authentication'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(http_method_names=['get', 'post']), name='logout'),
    path('register/', views.RegisterView.as_view(), name='register'),
]
