#!/usr/bin/env python3
"""
Django management command to set up Certificate Authority infrastructure
for proper PDF signing with revocation checking support.
"""

import os
from django.core.management.base import BaseCommand
from pdf_signature.certificate_authority import PDFSigningCA, setup_ca_infrastructure


class Command(BaseCommand):
    help = 'Set up Certificate Authority infrastructure for PDF signing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of existing certificates'
        )
        
        parser.add_argument(
            '--common-name',
            type=str,
            default='ARUL M',
            help='Common name for the signing certificate'
        )
        
        parser.add_argument(
            '--email',
            type=str,
            default='m.arul@fte.com',
            help='Email address for the signing certificate'
        )
        
        parser.add_argument(
            '--ca-dir',
            type=str,
            default='certificates/ca',
            help='Directory for CA files'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔧 Setting up Certificate Authority Infrastructure'))
        
        ca_dir = options['ca_dir']
        force = options['force']
        common_name = options['common_name']
        email = options['email']
        
        # Check if CA already exists
        ca = PDFSigningCA(ca_dir)
        ca_exists = os.path.exists(ca.ca_cert_path) and os.path.exists(ca.ca_key_path)
        cert_exists = os.path.exists(os.path.join('certificates', 'signing_cert.p12'))
        
        if ca_exists and cert_exists and not force:
            self.stdout.write(self.style.WARNING('⚠️  CA infrastructure already exists'))
            self.stdout.write('Use --force to recreate certificates')
            self.show_existing_info(ca)
            return
            
        if force and (ca_exists or cert_exists):
            self.stdout.write(self.style.WARNING('🔄 Recreating existing certificates...'))
            
        try:
            # Set up CA infrastructure
            self.stdout.write('📋 Creating Certificate Authority...')
            ca_cert, ca_private_key = ca.load_ca_certificate()
            
            self.stdout.write('🔑 Creating PDF signing certificate...')
            cert_path, ca_bundle_path = ca.create_pdf_signing_certificate(common_name, email)
            
            self.stdout.write('📜 Creating Certificate Revocation List...')
            crl_path = ca.create_crl()
            
            # Show success information
            self.stdout.write(self.style.SUCCESS('\n✅ Certificate Authority setup complete!'))
            self.stdout.write('')
            self.stdout.write('📁 Created files:')
            self.stdout.write(f'   🏛️  CA Certificate: {ca.ca_cert_path}')
            self.stdout.write(f'   🔐 CA Private Key: {ca.ca_key_path}')
            self.stdout.write(f'   📄 Signing Certificate: {cert_path}')
            self.stdout.write(f'   📦 CA Bundle: {ca_bundle_path}')
            self.stdout.write(f'   📜 CRL: {crl_path}')
            
            self.stdout.write('')
            self.stdout.write('🎯 Benefits of this setup:')
            self.stdout.write('   ✅ Proper CA-signed certificates (not self-signed)')
            self.stdout.write('   ✅ Certificate Revocation List (CRL) support')
            self.stdout.write('   ✅ Authority Information Access extensions')
            self.stdout.write('   ✅ Reduced Adobe Acrobat warnings')
            self.stdout.write('   ✅ Better certificate validation')
            
            self.stdout.write('')
            self.stdout.write('📋 Certificate Details:')
            self.stdout.write(f'   👤 Common Name: {common_name}')
            self.stdout.write(f'   📧 Email: {email}')
            self.stdout.write(f'   🏢 Organization: PERSONAL')
            self.stdout.write(f'   🌍 Country: IN (India)')
            self.stdout.write(f'   🏙️  State: Tamil Nadu')
            self.stdout.write(f'   📍 City: Chennai')
            
            self.stdout.write('')
            self.stdout.write('🔧 Next steps:')
            self.stdout.write('   1. Test PDF signing with new certificate')
            self.stdout.write('   2. Install CA certificate in Adobe Acrobat (optional)')
            self.stdout.write('   3. Configure CRL distribution if needed')
            
            # Test the certificate
            self.test_certificate(cert_path)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error setting up CA: {e}'))
            raise

    def show_existing_info(self, ca):
        """Show information about existing CA infrastructure."""
        self.stdout.write('')
        self.stdout.write('📋 Existing CA Infrastructure:')
        
        if os.path.exists(ca.ca_cert_path):
            self.stdout.write(f'   🏛️  CA Certificate: {ca.ca_cert_path}')
            
        if os.path.exists(ca.ca_key_path):
            self.stdout.write(f'   🔐 CA Private Key: {ca.ca_key_path}')
            
        cert_path = os.path.join('certificates', 'signing_cert.p12')
        if os.path.exists(cert_path):
            self.stdout.write(f'   📄 Signing Certificate: {cert_path}')
            
        ca_bundle_path = os.path.join('certificates', 'ca_bundle.pem')
        if os.path.exists(ca_bundle_path):
            self.stdout.write(f'   📦 CA Bundle: {ca_bundle_path}')
            
        if os.path.exists(ca.crl_path):
            self.stdout.write(f'   📜 CRL: {ca.crl_path}')

    def test_certificate(self, cert_path):
        """Test the created certificate."""
        self.stdout.write('')
        self.stdout.write('🧪 Testing certificate...')
        
        try:
            from pdf_signature.utils import load_certificate_data
            
            # Test loading the certificate
            private_key, certificate, ca_certificates = load_certificate_data()
            
            self.stdout.write('   ✅ Certificate loads successfully')
            self.stdout.write(f'   📅 Valid from: {certificate.not_valid_before_utc}')
            self.stdout.write(f'   📅 Valid until: {certificate.not_valid_after_utc}')
            self.stdout.write(f'   🔢 Serial number: {certificate.serial_number}')
            
            # Check extensions
            extensions = [ext.oid._name for ext in certificate.extensions]
            self.stdout.write(f'   🔧 Extensions: {len(extensions)} found')
            
            if 'cRLDistributionPoints' in extensions:
                self.stdout.write('   ✅ CRL Distribution Points: Present')
            else:
                self.stdout.write('   ⚠️  CRL Distribution Points: Missing')
                
            if 'authorityInfoAccess' in extensions:
                self.stdout.write('   ✅ Authority Information Access: Present')
            else:
                self.stdout.write('   ⚠️  Authority Information Access: Missing')
                
        except Exception as e:
            self.stdout.write(f'   ❌ Certificate test failed: {e}')

    def handle_ca_installation_guide(self):
        """Show guide for installing CA certificate in Adobe."""
        self.stdout.write('')
        self.stdout.write('📖 Installing CA Certificate in Adobe Acrobat:')
        self.stdout.write('')
        self.stdout.write('1. Open Adobe Acrobat Reader/Pro')
        self.stdout.write('2. Go to Edit → Preferences → Signatures')
        self.stdout.write('3. Click "Identities & Trusted Certificates"')
        self.stdout.write('4. Click "Trusted Certificates" → "Import"')
        self.stdout.write('5. Select the CA certificate file: certificates/ca/ca_cert.pem')
        self.stdout.write('6. Check "Use this certificate as a trusted root"')
        self.stdout.write('7. Click OK')
        self.stdout.write('')
        self.stdout.write('This will make Adobe trust certificates signed by your CA!')
