from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, View
from django.http import JsonResponse, HttpResponse, Http404
from django.core.files.storage import default_storage
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib import messages
import os
import json
import logging
from datetime import datetime
from .utils import (sign_pdf_cryptographically, verify_pdf_signature, get_certificate_info,
                   create_pdfa_compliant_signature, process_batch_signing, get_batch_job_status,
                   _sign_with_endesive, sign_each_page_with_endesive, sign_pdf_single_page,
                   sign_pdf_multi_page_with_proper_mdp)
from .forms import BatchPDFUploadForm, FolderSelectionForm
from .models import BatchSigningJob, PDFSigningTask
# USB key imports - commented out for simplified version
# from .usb_key_manager import usb_key_manager
# from .usb_key_signer import usb_key_signer

# Set up logging
logger = logging.getLogger(__name__)


class PDFSignatureView(LoginRequiredMixin, TemplateView):
    """
    Main PDF signature application view.
    Displays the upload interface for PDF documents.
    """
    template_name = 'pdf_signature/home.html'
    login_url = '/auth/login/'


class PDFUploadView(LoginRequiredMixin, View):
    """
    Handles PDF file upload and digital signature processing.
    Requires user authentication.
    """
    login_url = '/auth/login/'
    def post(self, request):
        """
        Process PDF upload (single or multiple files) and add digital signatures.
        Supports both single file and batch processing in the same endpoint.
        """
        try:
            # Check if this is a batch upload or single file upload
            files = request.FILES.getlist('pdf_files')  # For batch upload
            single_file = request.FILES.get('pdf_file')  # For single upload

            if not files and not single_file:
                logger.warning(f"No files uploaded by user {request.user.username}")
                return JsonResponse({'error': 'No files uploaded'}, status=400)

            # Convert single file to list for unified processing
            if single_file and not files:
                files = [single_file]

            # Validate all files
            for pdf_file in files:
                if not pdf_file.name.lower().endswith('.pdf'):
                    logger.warning(f"Invalid file type uploaded by user {request.user.username}: {pdf_file.name}")
                    return JsonResponse({'error': f'Please upload only PDF files. Invalid: {pdf_file.name}'}, status=400)

                if pdf_file.size > 10 * 1024 * 1024:
                    logger.warning(f"File too large uploaded by user {request.user.username}: {pdf_file.size} bytes")
                    return JsonResponse({'error': f'File size must be less than 10MB. Large file: {pdf_file.name}'}, status=400)

            # Get processing options
            apply_to_all_pages = request.POST.get('apply_to_all_pages', 'true').lower() == 'true'
            custom_save_path = request.POST.get('save_location', '').strip()
            processing_mode = request.POST.get('processing_mode', 'single')



            # USB key signing - disabled in simplified version
            use_usb_key = False  # request.POST.get('use_usb_key', 'false').lower() == 'true'
            usb_key_pin = ''  # request.POST.get('usb_key_pin', '').strip()

            # Process files
            if len(files) == 1:
                # Single file processing
                result = self.process_single_file(files[0], request.user, apply_to_all_pages, custom_save_path, use_usb_key, usb_key_pin)
                return JsonResponse(result)
            else:
                # Batch processing
                result = self.process_multiple_files(
                    files, request.user, apply_to_all_pages, custom_save_path
                )
                return JsonResponse(result)

        except Exception as e:
            logger.error(f"Error processing PDF upload for user {request.user.username}: {str(e)}")
            return JsonResponse({'error': 'An error occurred while processing the PDF(s)'}, status=500)

    def process_single_file(self, pdf_file, user, apply_to_all_pages, custom_save_path, use_usb_key=False, usb_key_pin=''):
        """Process a single PDF file with optional USB key signing."""
        try:
            # Save uploaded file with user-specific path
            safe_filename = f"{user.username}_{timezone.now().strftime('%Y%m%d_%H%M%S')}_{pdf_file.name}"
            file_path = default_storage.save(f'uploads/{safe_filename}', pdf_file)

            # Process the PDF and add signature
            signed_file_path = self.add_signature_to_pdf(file_path, user, apply_to_all_pages, custom_save_path, use_usb_key, usb_key_pin)

            logger.info(f"Single PDF signed successfully by user {user.username}: {signed_file_path}")

            # Determine if file is in default location or custom location
            is_custom_location = custom_save_path and custom_save_path.strip()

            # Prepare response data
            response_data = {
                'success': True,
                'filename': os.path.basename(signed_file_path),
                'multi_page_signing': apply_to_all_pages,
                'apply_to_all_pages': apply_to_all_pages,
                'file_size': os.path.getsize(signed_file_path) if os.path.exists(signed_file_path) else 0
            }

            if is_custom_location:
                # File saved to custom location - provide save location info instead of download URL
                response_data['save_location'] = os.path.dirname(signed_file_path)
                response_data['full_path'] = signed_file_path
                response_data['download_url'] = None  # No download URL for custom locations
                logger.info(f"File saved to custom location: {signed_file_path}")
            else:
                # File saved to default location - provide download URL
                response_data['download_url'] = f'/pdf-signature/download/{os.path.basename(signed_file_path)}/'
                response_data['save_location'] = None
                logger.info(f"File saved to default location, download URL: {response_data['download_url']}")

            return response_data

        except Exception as e:
            logger.error(f"Error processing single PDF for user {user.username}: {str(e)}")
            return {'success': False, 'error': f'Failed to process PDF: {str(e)}'}

    def process_multiple_files(self, files, user, apply_to_all_pages, custom_save_path):
        """Process multiple PDF files using batch processing."""
        try:
            # Use the existing batch processing function
            results = process_batch_signing(
                files=files,
                user=user,
                save_location=custom_save_path,
                naming_convention='signed_{original_name}',
                custom_naming_pattern='',
                apply_to_all_pages=apply_to_all_pages
            )

            logger.info(f"Batch PDF signing completed for user {user.username}: {results['successful_files']}/{results['total_files']} successful")

            return {
                'success': True,
                'total_files': results['total_files'],
                'successful_files': results['successful_files'],
                'failed_files': results['failed_files'],
                'processed_files': results['processed_files'],
                'errors': results['errors'],
                'multi_page_signing': apply_to_all_pages,
                'batch_job_id': results.get('batch_job_id')
            }
        except Exception as e:
            logger.error(f"Error processing batch PDFs for user {user.username}: {str(e)}")
            return {'success': False, 'error': f'Failed to process batch PDFs: {str(e)}'}

    def add_signature_to_pdf(self, file_path, user, apply_to_all_pages=True, custom_save_path=None, use_usb_key=False, usb_key_pin=''):
        """
        Add enhanced cryptographic digital signature to PDF using X.509 certificate or USB key.
        Uses PDF/A compliant signatures for maximum compatibility with PDF readers.
        Supports multi-page signature application, custom save locations, and USB key signing.
        """
        try:
            # Import the resolve function
            from .utils import resolve_custom_save_path

            # Get full paths
            input_path = os.path.join(settings.MEDIA_ROOT, file_path)
            signed_filename = f"signed_{os.path.basename(file_path)}"

            logger.info(f"Processing PDF signature for user {user.username}")
            logger.info(f"Input file: {input_path}")
            logger.info(f"Custom save path provided: {custom_save_path}")

            # Handle custom save path properly
            if custom_save_path and custom_save_path.strip():
                try:
                    signed_path = resolve_custom_save_path(custom_save_path.strip(), signed_filename, user)
                    logger.info(f"Using custom save location: {signed_path}")
                except Exception as path_error:
                    logger.error(f"Failed to resolve custom save path '{custom_save_path}': {path_error}")
                    # Fall back to default location
                    signed_path = os.path.join(settings.MEDIA_ROOT, 'signed', signed_filename)
                    logger.warning(f"Falling back to default save location: {signed_path}")
            else:
                signed_path = os.path.join(settings.MEDIA_ROOT, 'signed', signed_filename)
                logger.info(f"Using default save location: {signed_path}")

            # Create signed directory if it doesn't exist (for default location)
            if not custom_save_path or not custom_save_path.strip():
                os.makedirs(os.path.dirname(signed_path), exist_ok=True)

            # Use improved signing implementation with proper DocMDP enforcement
            try:
                # Determine if PDF is single-page or multi-page (for logging purposes)
                try:
                    page_count = get_pdf_page_count(input_path)
                    if page_count == 1:
                        logger.info(f"Detected single-page PDF, using improved implementation: {input_path} -> {signed_path}")
                        # Use dedicated single-page function (which internally calls the improved multi-page implementation)
                        result_path = sign_pdf_single_page(input_path, signed_path, user)
                    else:
                        logger.info(f"Detected {page_count}-page PDF, using improved implementation: {input_path} -> {signed_path}")
                        # Use improved multi-page implementation directly
                        result_path = sign_pdf_multi_page_with_proper_mdp(input_path, signed_path, user)
                except Exception as page_count_error:
                    # If we can't determine page count, default to improved multi-page implementation
                    logger.warning(f"Could not determine page count ({page_count_error}), using improved multi-page implementation")
                    result_path = sign_pdf_multi_page_with_proper_mdp(input_path, signed_path, user)

                logger.info("CRITICAL: Both single-page and multi-page PDFs now use improved implementation")
                logger.info("CRITICAL: Certification signature applied FIRST for proper document protection")

                # Verify the file was actually created
                if os.path.exists(result_path):
                    file_size = os.path.getsize(result_path)
                    logger.info(f"PDF signed successfully: {signed_filename} by user {user.username}")
                    logger.info(f"Signed file created at: {result_path} ({file_size} bytes)")
                else:
                    raise Exception(f"Signed file was not created at expected location: {result_path}")

            except Exception as signing_error:
                logger.error(f"PDF signing failed: {signing_error}")
                raise signing_error

            return result_path

        except Exception as e:
            logger.error(f"Error adding cryptographic signature: {str(e)} for user {user.username}")
            raise Exception(f"Failed to sign PDF: {str(e)}")


class PDFVerifyView(LoginRequiredMixin, View):
    """
    View for verifying PDF signatures.
    """

    def get(self, request):
        """Display the PDF verification page."""
        return render(request, 'pdf_signature/verify.html')

    def post(self, request):
        """Process PDF verification request."""
        try:
            # Validate file upload
            if 'pdf_file' not in request.FILES:
                logger.warning(f"No file uploaded for verification by user {request.user.username}")
                return JsonResponse({'error': 'No file uploaded'}, status=400)

            pdf_file = request.FILES['pdf_file']

            # Validate file type
            if not pdf_file.name.lower().endswith('.pdf'):
                logger.warning(f"Invalid file type uploaded for verification by user {request.user.username}: {pdf_file.name}")
                return JsonResponse({'error': 'Please upload a PDF file'}, status=400)

            # Validate file size (10MB limit)
            if pdf_file.size > 10 * 1024 * 1024:
                logger.warning(f"File too large uploaded for verification by user {request.user.username}: {pdf_file.size} bytes")
                return JsonResponse({'error': 'File size must be less than 10MB'}, status=400)

            # Save uploaded file temporarily for verification
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                for chunk in pdf_file.chunks():
                    temp_file.write(chunk)
                temp_file_path = temp_file.name

            try:
                # Verify the PDF signature
                from pdf_signature.utils import verify_pdf_signature

                verification_result = verify_pdf_signature(temp_file_path)
                verification_type = 'standard'

                logger.info(f"PDF signature verification completed for user {request.user.username}: {pdf_file.name}")

                return JsonResponse({
                    'success': True,
                    'verification_type': verification_type,
                    'filename': pdf_file.name,
                    'result': verification_result
                })

            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file_path)
                except:
                    pass

        except Exception as e:
            logger.error(f"Error verifying PDF for user {request.user.username}: {str(e)}")
            return JsonResponse({'error': 'An error occurred while verifying the PDF'}, status=500)


class PDFDownloadView(LoginRequiredMixin, View):
    """
    Handles secure download of signed PDF files.
    Requires user authentication and validates file access.
    """
    login_url = '/auth/login/'

    def get(self, request, filename):
        """
        Serve signed PDF file for download with security checks.
        """
        try:
            file_path = os.path.join(settings.MEDIA_ROOT, 'signed', filename)

            # Security check: ensure file exists and is within allowed directory
            if not os.path.exists(file_path):
                logger.warning(f"File not found: {filename} requested by user {request.user.username}")
                raise Http404("File not found")

            # Additional security: check if file path is within expected directory
            if not os.path.abspath(file_path).startswith(os.path.abspath(os.path.join(settings.MEDIA_ROOT, 'signed'))):
                logger.warning(f"Unauthorized file access attempt: {filename} by user {request.user.username}")
                raise Http404("File not found")

            # Log download
            logger.info(f"PDF download: {filename} by user {request.user.username}")

            with open(file_path, 'rb') as file:
                response = HttpResponse(file.read(), content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="{filename}"'
                response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response['Pragma'] = 'no-cache'
                response['Expires'] = '0'
                return response

        except Exception as e:
            logger.error(f"Error downloading PDF {filename} for user {request.user.username}: {str(e)}")
            raise Http404("File not found")


class PDFVerificationView(LoginRequiredMixin, TemplateView):
    """
    Handles PDF signature verification functionality.
    Displays verification interface and processes verification requests.
    """
    template_name = 'pdf_signature/verify.html'
    login_url = '/auth/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['certificate_info'] = get_certificate_info()
        return context


class PDFVerifyUploadView(LoginRequiredMixin, View):
    """
    Handles PDF file upload for signature verification.
    Requires user authentication.
    """
    login_url = '/auth/login/'

    def post(self, request):
        """
        Process PDF upload and verify digital signature.
        """
        try:
            # Validate file upload
            if 'pdf_file' not in request.FILES:
                logger.warning(f"No file uploaded for verification by user {request.user.username}")
                return JsonResponse({'error': 'No file uploaded'}, status=400)

            pdf_file = request.FILES['pdf_file']

            # Validate file type
            if not pdf_file.name.lower().endswith('.pdf'):
                logger.warning(f"Invalid file type uploaded for verification by user {request.user.username}: {pdf_file.name}")
                return JsonResponse({'error': 'Please upload a PDF file'}, status=400)

            # Validate file size (10MB limit)
            if pdf_file.size > 10 * 1024 * 1024:
                logger.warning(f"File too large uploaded for verification by user {request.user.username}: {pdf_file.size} bytes")
                return JsonResponse({'error': 'File size must be less than 10MB'}, status=400)

            # Save uploaded file temporarily for verification
            temp_filename = f"verify_{request.user.username}_{timezone.now().strftime('%Y%m%d_%H%M%S')}_{pdf_file.name}"
            temp_file_path = default_storage.save(f'temp/{temp_filename}', pdf_file)
            full_temp_path = os.path.join(settings.MEDIA_ROOT, temp_file_path)

            # Verify the PDF signature
            verification_result = verify_pdf_signature(full_temp_path)

            # Clean up temporary file
            try:
                os.remove(full_temp_path)
            except:
                pass  # Ignore cleanup errors

            logger.info(f"PDF signature verification completed by user {request.user.username}: {pdf_file.name}")

            return JsonResponse({
                'success': True,
                'verification_result': verification_result,
                'filename': pdf_file.name
            })

        except Exception as e:
            logger.error(f"Error verifying PDF signature for user {request.user.username}: {str(e)}")
            return JsonResponse({'error': 'An error occurred while verifying the PDF signature'}, status=500)


class BatchPDFSigningView(LoginRequiredMixin, TemplateView):
    """
    Batch PDF signing interface view.
    """
    template_name = 'pdf_signature/batch_sign.html'
    login_url = '/auth/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = BatchPDFUploadForm()
        context['certificate_info'] = get_certificate_info()
        return context


class BatchPDFUploadView(LoginRequiredMixin, View):
    """
    Handles batch PDF file upload and digital signature processing.
    """
    login_url = '/auth/login/'

    def post(self, request):
        """
        Process batch PDF upload and add digital signatures.
        """
        try:
            form = BatchPDFUploadForm(request.POST, request.FILES)

            if not form.is_valid():
                errors = []
                for field, field_errors in form.errors.items():
                    for error in field_errors:
                        errors.append(f"{field}: {error}")
                return JsonResponse({'error': '; '.join(errors)}, status=400)

            # Get form data
            files = request.FILES.getlist('pdf_files')
            save_location = form.cleaned_data.get('save_location')
            naming_convention = form.cleaned_data.get('naming_convention')
            custom_naming_pattern = form.cleaned_data.get('custom_naming_pattern')
            apply_to_all_pages = form.cleaned_data.get('apply_to_all_pages', True)

            if not files:
                return JsonResponse({'error': 'No files uploaded'}, status=400)

            logger.info(f"Starting batch PDF signing for user {request.user.username}: {len(files)} files")

            # Process batch signing
            results = process_batch_signing(
                files=files,
                user=request.user,
                save_location=save_location,
                naming_convention=naming_convention,
                custom_naming_pattern=custom_naming_pattern,
                apply_to_all_pages=apply_to_all_pages
            )

            return JsonResponse({
                'success': True,
                'batch_job_id': results['batch_job_id'],
                'total_files': results['total_files'],
                'successful_files': results['successful_files'],
                'failed_files': results['failed_files'],
                'processed_files': results['processed_files'],
                'errors': results['errors']
            })

        except Exception as e:
            logger.error(f"Error processing batch PDF upload for user {request.user.username}: {str(e)}")
            return JsonResponse({'error': 'An error occurred while processing the batch upload'}, status=500)


class BatchJobStatusView(LoginRequiredMixin, View):
    """
    Get status of a batch signing job.
    """
    login_url = '/auth/login/'

    def get(self, request, job_id):
        """
        Get batch job status.
        """
        try:
            status = get_batch_job_status(job_id, request.user)
            return JsonResponse(status)
        except Exception as e:
            logger.error(f"Error getting batch job status for user {request.user.username}: {str(e)}")
            return JsonResponse({'error': 'An error occurred while getting job status'}, status=500)


class BatchJobListView(LoginRequiredMixin, TemplateView):
    """
    List all batch jobs for the current user.
    """
    template_name = 'pdf_signature/batch_jobs.html'
    login_url = '/auth/login/'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get recent batch jobs for the user
        batch_jobs = BatchSigningJob.objects.filter(user=self.request.user)[:20]
        context['batch_jobs'] = batch_jobs

        return context


class FolderSelectionView(LoginRequiredMixin, View):
    """
    Handle folder selection for save location.
    """
    login_url = '/auth/login/'

    def post(self, request):
        """
        Process folder selection.
        """
        try:
            form = FolderSelectionForm(request.POST)
            if form.is_valid():
                selected_folder = form.cleaned_data['selected_folder']

                # Validate folder exists and is accessible
                if os.path.exists(selected_folder) and os.path.isdir(selected_folder):
                    return JsonResponse({
                        'success': True,
                        'selected_folder': selected_folder
                    })
                else:
                    return JsonResponse({'error': 'Selected folder does not exist or is not accessible'}, status=400)
            else:
                return JsonResponse({'error': 'Invalid folder selection'}, status=400)

        except Exception as e:
            logger.error(f"Error processing folder selection for user {request.user.username}: {str(e)}")
            return JsonResponse({'error': 'An error occurred while selecting folder'}, status=500)


class USBKeyDetectionView(LoginRequiredMixin, View):
    """
    USB Key detection and management API.
    """
    login_url = '/auth/login/'

    def get(self, request):
        """
        Detect available USB keys.
        """
        try:
            detected_keys = usb_key_manager.detect_usb_keys()

            response_data = {
                'success': True,
                'detected_keys': detected_keys,
                'total_keys': len(detected_keys)
            }

            if detected_keys:
                # Add simplified token list for frontend
                tokens = []
                for key_info in detected_keys:
                    if key_info.get('tokens'):
                        for token in key_info['tokens']:
                            tokens.append({
                                'label': token['label'],
                                'manufacturer': token['manufacturer'],
                                'model': token['model'],
                                'library_path': key_info['library_path'],
                                'vendor': key_info['vendor']
                            })
                response_data['available_tokens'] = tokens

            logger.info(f"USB key detection completed for user {request.user.username}: {len(detected_keys)} keys found")
            return JsonResponse(response_data)

        except Exception as e:
            logger.error(f"Error detecting USB keys for user {request.user.username}: {str(e)}")
            return JsonResponse({'error': 'An error occurred while detecting USB keys'}, status=500)

    def post(self, request):
        """
        Test USB key connection.
        """
        try:
            data = json.loads(request.body)
            library_path = data.get('library_path')
            token_label = data.get('token_label')
            pin = data.get('pin')

            if not all([library_path, token_label, pin]):
                return JsonResponse({'error': 'Missing required parameters'}, status=400)

            # Test connection
            success = usb_key_signer.initialize_usb_key(library_path, token_label, pin)

            if success:
                # Get key info
                key_info = usb_key_signer.get_usb_key_info()
                usb_key_signer.cleanup()  # Clean up test connection

                return JsonResponse({
                    'success': True,
                    'message': 'USB key connection successful',
                    'key_info': key_info
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Failed to connect to USB key'
                })

        except Exception as e:
            logger.error(f"Error testing USB key connection for user {request.user.username}: {str(e)}")
            return JsonResponse({'error': f'Connection test failed: {str(e)}'}, status=500)
