"""
Django management command to test PDF signing functionality.
Usage: python manage.py test_pdf_signing
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from pdf_signature.utils import (
    sign_pdf_cryptographically,
    verify_pdf_signature,
    create_pdfa_compliant_signature,
    ENDESIVE_AVAILABLE,
    _sign_with_endesive,
    CERTIFICATE_P12_PATH
)
import os
from datetime import datetime


class Command(BaseCommand):
    help = 'Test PDF signing functionality with updated endesive implementation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--input',
            type=str,
            default='sample.pdf',
            help='Input PDF file to sign (default: sample.pdf)'
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output PDF file name (default: auto-generated)'
        )
        parser.add_argument(
            '--verify',
            action='store_true',
            help='Also verify the signed PDF'
        )
        parser.add_argument(
            '--export-certs',
            action='store_true',
            help='Export certificate files for deployment'
        )
        parser.add_argument(
            '--individual-pages',
            action='store_true',
            help='Test individual page signatures (each page gets its own cryptographic signature)'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('DJANGO PDF SIGNING TEST'))
        self.stdout.write(self.style.SUCCESS('=' * 60))

        # Check endesive availability
        self.stdout.write(f"Endesive Available: {ENDESIVE_AVAILABLE}")
        if not ENDESIVE_AVAILABLE:
            self.stdout.write(self.style.ERROR("ERROR: Endesive library not available"))
            return

        # Check certificate exists
        try:
            cert_path = CERTIFICATE_P12_PATH
            self.stdout.write(f"Certificate Path: {cert_path}")
            self.stdout.write(f"Certificate Exists: {os.path.exists(cert_path)}")
            if not os.path.exists(cert_path):
                self.stdout.write(self.style.WARNING(f"WARNING: Certificate file not found at {cert_path}"))
                self.stdout.write(self.style.WARNING("Please ensure certificate is properly configured"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"ERROR: Failed to check certificate: {e}"))
            return

        # Get input file
        input_pdf = options['input']
        if not os.path.exists(input_pdf):
            self.stdout.write(self.style.ERROR(f"ERROR: Input PDF not found: {input_pdf}"))
            return

        # Generate output filename
        if options['output']:
            output_pdf = options['output']
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_pdf = f"django_signed_{timestamp}.pdf"

        # Get or create a test user
        try:
            test_user = User.objects.filter(is_superuser=True).first()
            if not test_user:
                test_user = User.objects.create_user(
                    username='test_signer',
                    email='test@example.com',
                    password='testpass123'
                )
            self.stdout.write(f"Using test user: {test_user.username}")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Warning: Could not get test user: {e}"))
            test_user = None

        # Test PDF signing
        try:
            self.stdout.write(f"\nTesting PDF signing...")
            self.stdout.write(f"Input PDF: {input_pdf}")
            self.stdout.write(f"Output PDF: {output_pdf}")

            # Sign the PDF
            if options['individual_pages']:
                self.stdout.write(f"Using individual page signatures (each page gets its own cryptographic signature)...")
                try:
                    from pdf_signature.utils import sign_each_page_individually_with_endesive
                    result_path = sign_each_page_individually_with_endesive(input_pdf, output_pdf, test_user)
                except ImportError:
                    self.stdout.write(self.style.WARNING("Individual page signing not available, using standard signing"))
                    result_path = sign_pdf_cryptographically(input_pdf, output_pdf, test_user)
            else:
                result_path = sign_pdf_cryptographically(input_pdf, output_pdf, test_user)

            if os.path.exists(result_path):
                file_size = os.path.getsize(result_path)
                self.stdout.write(self.style.SUCCESS(f"[SUCCESS] PDF signed successfully!"))
                self.stdout.write(self.style.SUCCESS(f"[SUCCESS] Output file: {result_path}"))
                self.stdout.write(self.style.SUCCESS(f"[SUCCESS] File size: {file_size} bytes"))

                # Verify PDF header
                with open(result_path, 'rb') as f:
                    header = f.read(8)
                    if header.startswith(b'%PDF-'):
                        self.stdout.write(self.style.SUCCESS(f"[SUCCESS] Valid PDF header: {header.decode('ascii', errors='ignore')}"))
                    else:
                        self.stdout.write(self.style.ERROR(f"[ERROR] Invalid PDF header: {header}"))
                        return

                # Test verification if requested
                if options['verify']:
                    self.stdout.write(f"\nTesting signature verification...")

                    if options['individual_pages']:
                        # Use specialized verification for individual page signatures
                        try:
                            from pdf_signature.utils import verify_individual_page_signatures
                            verification_result = verify_individual_page_signatures(result_path)

                            self.stdout.write(f"Individual Page Signature Verification Result:")
                            self.stdout.write(f"  - Total pages: {verification_result.get('total_pages', 0)}")
                            self.stdout.write(f"  - Total signatures: {verification_result.get('total_signatures', 0)}")
                            self.stdout.write(f"  - Individual page signatures: {verification_result.get('individual_page_signatures', False)}")
                            self.stdout.write(f"  - Overall valid: {verification_result.get('overall_valid', False)}")

                            if verification_result.get('page_signature_details'):
                                for detail in verification_result['page_signature_details']:
                                    self.stdout.write(f"  Signature {detail['signature_index']}:")
                                    self.stdout.write(f"    - Valid: {detail['valid']}")
                                    self.stdout.write(f"    - Signer: {detail['signer']}")
                                    self.stdout.write(f"    - Certificate Valid: {detail['certificate_valid']}")
                                    self.stdout.write(f"    - Coverage: {detail['covers_pages']}")

                            if verification_result.get('errors'):
                                self.stdout.write(f"  - Errors: {verification_result.get('errors', [])}")
                        except ImportError:
                            self.stdout.write(self.style.WARNING("Individual page verification not available, using standard verification"))
                            verification_result = verify_pdf_signature(result_path)
                    else:
                        # Standard verification
                        verification_result = verify_pdf_signature(result_path)

                        self.stdout.write(f"Verification Result:")
                        self.stdout.write(f"  - Valid: {verification_result.get('is_valid', False)}")
                        self.stdout.write(f"  - Signatures found: {len(verification_result.get('signatures', []))}")
                        self.stdout.write(f"  - Document modified: {verification_result.get('document_modified', False)}")

                        if verification_result.get('errors'):
                            self.stdout.write(f"  - Errors: {verification_result.get('errors', [])}")

                        if verification_result.get('signatures'):
                            for i, sig in enumerate(verification_result['signatures']):
                                self.stdout.write(f"  Signature {i+1}:")
                                self.stdout.write(f"    - Signer: {sig.get('signer', 'Unknown')}")
                                self.stdout.write(f"    - Valid: {sig.get('is_valid', False)}")
                                self.stdout.write(f"    - Certificate Valid: {sig.get('certificate_valid', False)}")
                                self.stdout.write(f"    - Document Integrity: {sig.get('document_integrity', False)}")
                                self.stdout.write(f"    - Timezone: {sig.get('timezone', 'Not specified')}")
                                self.stdout.write(f"    - Covers all pages: {sig.get('covers_all_pages', 'Unknown')}")

                self.stdout.write(self.style.SUCCESS(f"\n[SUCCESS] Test completed successfully!"))
                self.stdout.write(self.style.SUCCESS(f"[SUCCESS] Signed PDF saved as: {result_path}"))
                self.stdout.write(f"\nYou can now test this PDF in:")
                self.stdout.write(f"  - Adobe Acrobat Reader")
                self.stdout.write(f"  - Microsoft Edge PDF viewer")
                self.stdout.write(f"  - Other PDF readers")
                self.stdout.write(f"\nSignature appearance includes:")
                self.stdout.write(f"  - 'Digitally Signed by:' (font size 10)")
                self.stdout.write(f"  - 'M.ARUL' (font size 12)")
                self.stdout.write(f"  - Current date and time")
                self.stdout.write(f"  - 'Chennai GMT (+05:30)' timezone information")

            else:
                self.stdout.write(self.style.ERROR(f"[ERROR] Signed PDF was not created"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[ERROR] PDF signing failed: {e}"))
            import traceback
            traceback.print_exc()

        self.stdout.write(self.style.SUCCESS('=' * 60))
