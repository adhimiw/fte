from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.views import LoginView as DjangoLoginView, LogoutView as DjangoLogoutView
from django.contrib.auth.forms import UserCreationForm
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator


class LoginView(DjangoLoginView):
    """
    Custom login view that redirects authenticated users and provides
    proper success URL handling.
    """
    template_name = 'authentication/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('dashboard:home')

    def form_invalid(self, form):
        messages.error(self.request, 'Invalid username or password. Please try again.')
        return super().form_invalid(form)


class LogoutView(DjangoLogoutView):
    """
    Custom logout view that redirects to login page after logout.
    """
    next_page = 'authentication:login'  # Using URL name instead of reverse_lazy

    def dispatch(self, request, *args, **kwargs):
        messages.success(request, 'You have been successfully logged out.')
        return super().dispatch(request, *args, **kwargs)


class RegisterView(CreateView):
    """
    Custom registration view that creates new user accounts.
    Redirects authenticated users to dashboard.
    """
    form_class = UserCreationForm
    template_name = 'authentication/register.html'
    success_url = reverse_lazy('authentication:login')

    def form_valid(self, form):
        response = super().form_valid(form)
        username = form.cleaned_data.get('username')
        messages.success(
            self.request,
            f'Account created for {username}! You can now log in with your credentials.'
        )
        return response

    def form_invalid(self, form):
        messages.error(
            self.request,
            'There was an error creating your account. Please check the form and try again.'
        )
        return super().form_invalid(form)

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('dashboard:home')
        return super().dispatch(request, *args, **kwargs)
