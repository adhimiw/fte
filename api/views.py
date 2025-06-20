from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from pdf_signature.views import PDFUploadView as PDFUploadViewBase
import logging

# Set up logging
logger = logging.getLogger(__name__)


class LoginAPIView(APIView):
    """
    API endpoint for user authentication.
    Allows anonymous access for login attempts.
    """
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        """
        Authenticate user with username and password.
        """
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            logger.warning(f"Login attempt with missing credentials from IP: {request.META.get('REMOTE_ADDR')}")
            return Response({
                'success': False,
                'message': 'Username and password are required'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=username, password=password)
        if user:
            if user.is_active:
                login(request, user)
                logger.info(f"Successful API login for user: {username}")
                return Response({
                    'success': True,
                    'message': 'Login successful',
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'is_superuser': user.is_superuser,
                        'last_login': user.last_login
                    }
                })
            else:
                logger.warning(f"Login attempt for inactive user: {username}")
                return Response({
                    'success': False,
                    'message': 'Account is disabled'
                }, status=status.HTTP_401_UNAUTHORIZED)
        else:
            logger.warning(f"Failed login attempt for username: {username} from IP: {request.META.get('REMOTE_ADDR')}")
            return Response({
                'success': False,
                'message': 'Invalid username or password'
            }, status=status.HTTP_401_UNAUTHORIZED)


class LogoutAPIView(APIView):
    """
    API endpoint for user logout.
    Requires authentication.
    """
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]

    def post(self, request):
        """
        Log out the current user.
        """
        username = request.user.username
        logout(request)
        logger.info(f"User logged out via API: {username}")
        return Response({
            'success': True,
            'message': 'Logout successful'
        })


class PDFUploadAPIView(APIView):
    """
    API endpoint for PDF upload and digital signature.
    Requires authentication and handles file processing.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    throttle_classes = [UserRateThrottle]

    def post(self, request):
        # Reuse the logic from the PDF upload view
        pdf_upload_view = PDFUploadViewBase()
        pdf_upload_view.request = request

        try:
            if 'pdf_file' not in request.FILES:
                return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)

            pdf_file = request.FILES['pdf_file']

            if not pdf_file.name.endswith('.pdf'):
                return Response({'error': 'Please upload a PDF file'}, status=status.HTTP_400_BAD_REQUEST)

            # Process the PDF using improved implementation
            from django.core.files.storage import default_storage
            file_path = default_storage.save(f'uploads/{pdf_file.name}', pdf_file)
            # The add_signature_to_pdf method now uses improved implementation with proper DocMDP enforcement
            signed_file_path = pdf_upload_view.add_signature_to_pdf(file_path)

            return Response({
                'success': True,
                'message': 'PDF signed successfully',
                'download_url': f'/pdf-signature/download/{os.path.basename(signed_file_path)}/',
                'filename': os.path.basename(signed_file_path)
            })

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
