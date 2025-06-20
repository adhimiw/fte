from django.core.management.base import BaseCommand
from pdf_signature.utils import create_self_signed_certificate, get_certificate_info
import os
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Create a new self-signed certificate for PDF signing'

    def handle(self, *args, **options):
        self.stdout.write("Creating a new self-signed certificate...")
        try:
            # Create the certificates directory if it doesn't exist
            cert_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'certificates')
            os.makedirs(cert_dir, exist_ok=True)
            
            # Generate the certificate
            cert_info = create_self_signed_certificate()
            
            if cert_info:
                self.stdout.write(
                    self.style.SUCCESS('Successfully created self-signed certificate:')
                )
                self.stdout.write(f"Certificate: {cert_info.get('cert_path', 'N/A')}")
                self.stdout.write(f"Private Key: {cert_info.get('key_path', 'N/A')}")
                self.stdout.write(f"PKCS#12 Bundle: {cert_info.get('p12_path', 'N/A')}")
                
                # Display certificate info
                cert_info = get_certificate_info()
                self.stdout.write("\nCertificate Information:")
                self.stdout.write(f"Subject: {cert_info.get('subject', 'N/A')}")
                self.stdout.write(f"Issuer: {cert_info.get('issuer', 'N/A')}")
                self.stdout.write(f"Valid From: {cert_info.get('not_before', 'N/A')}")
                self.stdout.write(f"Valid Until: {cert_info.get('not_after', 'N/A')}")
            else:
                self.stdout.write(
                    self.style.ERROR('Failed to create certificate. Check logs for details.')
                )
        except Exception as e:
            logger.exception("Error creating certificate:")
            self.stdout.write(
                self.style.ERROR(f'Error creating certificate: {str(e)}')
            )
