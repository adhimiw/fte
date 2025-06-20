from django.shortcuts import render
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.urls import reverse


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Main dashboard view that displays available applications in a tile layout.
    Requires user authentication.
    """
    template_name = 'dashboard/home.html'
    login_url = '/auth/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Define available applications
        context['apps'] = [
            {
                'name': 'PDF Digital Signature',
                'description': 'Upload and digitally sign PDF documents with timestamp and location',
                'url': reverse('pdf_signature:home'),
                'icon': 'fas fa-file-signature',
                'color': 'primary',
                'status': 'active'
            },
            # Future apps can be added here
            # Example:
            # {
            #     'name': 'Document Manager',
            #     'description': 'Manage and organize your documents',
            #     'url': '/document-manager/',
            #     'icon': 'fas fa-folder',
            #     'color': 'success',
            #     'status': 'coming_soon'
            # },
        ]

        # Add user statistics
        context['user_stats'] = {
            'total_apps': len([app for app in context['apps'] if app.get('status') == 'active']),
            'last_login': self.request.user.last_login,
            'username': self.request.user.username,
            'is_superuser': self.request.user.is_superuser,
        }

        return context
