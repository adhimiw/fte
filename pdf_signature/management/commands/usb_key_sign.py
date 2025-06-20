#!/usr/bin/env python3
"""
Django management command for USB key PDF signing operations.
Provides automated signing capabilities using hardware security modules.
"""

import os
import sys
import getpass
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from pdf_signature.usb_key_manager import usb_key_manager
from pdf_signature.usb_key_signer import usb_key_signer


class Command(BaseCommand):
    help = 'USB Key PDF Signing Operations - Automate PDF signing with hardware security modules'

    def add_arguments(self, parser):
        parser.add_argument(
            '--detect',
            action='store_true',
            help='Detect available USB keys and PKCS#11 libraries'
        )
        
        parser.add_argument(
            '--list-tokens',
            action='store_true',
            help='List tokens on detected USB keys'
        )
        
        parser.add_argument(
            '--sign',
            type=str,
            help='Sign a PDF file (provide input PDF path)'
        )
        
        parser.add_argument(
            '--sign-batch',
            type=str,
            help='Sign multiple PDF files in a directory'
        )
        
        parser.add_argument(
            '--individual-pages',
            action='store_true',
            help='Sign each page individually (use with --sign or --sign-batch)'
        )
        
        parser.add_argument(
            '--output',
            type=str,
            help='Output path for signed PDF (use with --sign)'
        )
        
        parser.add_argument(
            '--library',
            type=str,
            help='Path to PKCS#11 library (auto-detected if not specified)'
        )
        
        parser.add_argument(
            '--token',
            type=str,
            help='Token label to use (auto-selected if not specified)'
        )
        
        parser.add_argument(
            '--pin',
            type=str,
            help='PIN for the USB key (will prompt if not provided)'
        )
        
        parser.add_argument(
            '--info',
            action='store_true',
            help='Show information about connected USB key'
        )

    def handle(self, *args, **options):
        try:
            if options['detect']:
                self.detect_usb_keys()
            elif options['list_tokens']:
                self.list_tokens()
            elif options['sign']:
                self.sign_pdf(options)
            elif options['sign_batch']:
                self.sign_batch(options)
            elif options['info']:
                self.show_usb_key_info()
            else:
                self.print_help()
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nOperation cancelled by user'))
            sys.exit(1)
        except Exception as e:
            raise CommandError(f'Error: {e}')

    def detect_usb_keys(self):
        """Detect available USB keys."""
        self.stdout.write(self.style.SUCCESS('🔍 Detecting USB keys...'))
        
        detected_keys = usb_key_manager.detect_usb_keys()
        
        if not detected_keys:
            self.stdout.write(self.style.WARNING('❌ No USB keys detected'))
            self.stdout.write('Make sure your USB key is connected and drivers are installed.')
            return
            
        self.stdout.write(self.style.SUCCESS(f'✅ Found {len(detected_keys)} USB key(s):'))
        
        for i, key_info in enumerate(detected_keys, 1):
            self.stdout.write(f'\n📱 USB Key #{i}:')
            self.stdout.write(f'   Vendor: {key_info["vendor"]}')
            self.stdout.write(f'   Library: {key_info["library_path"]}')
            self.stdout.write(f'   Status: {key_info["status"]}')
            
            if key_info.get('tokens'):
                self.stdout.write(f'   Tokens: {len(key_info["tokens"])}')
                for j, token in enumerate(key_info['tokens'], 1):
                    self.stdout.write(f'     Token #{j}:')
                    self.stdout.write(f'       Label: {token["label"]}')
                    self.stdout.write(f'       Manufacturer: {token["manufacturer"]}')
                    self.stdout.write(f'       Model: {token["model"]}')
                    self.stdout.write(f'       Serial: {token["serial"]}')

    def list_tokens(self):
        """List tokens on detected USB keys."""
        self.stdout.write(self.style.SUCCESS('🔍 Listing USB key tokens...'))
        
        detected_keys = usb_key_manager.detect_usb_keys()
        
        if not detected_keys:
            self.stdout.write(self.style.WARNING('❌ No USB keys detected'))
            return
            
        for key_info in detected_keys:
            if key_info.get('tokens'):
                self.stdout.write(f'\n📱 {key_info["vendor"]} USB Key:')
                for token in key_info['tokens']:
                    self.stdout.write(f'   🔑 {token["label"]} ({token["manufacturer"]} {token["model"]})')

    def sign_pdf(self, options):
        """Sign a single PDF file."""
        input_path = options['sign']
        
        if not os.path.exists(input_path):
            raise CommandError(f'Input file not found: {input_path}')
            
        # Generate output path if not provided
        if options['output']:
            output_path = options['output']
        else:
            base_name = os.path.splitext(input_path)[0]
            timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"{base_name}_usb_signed_{timestamp}.pdf"
            
        # Initialize USB key
        if not self._initialize_usb_key(options):
            return
            
        try:
            self.stdout.write(f'📄 Signing PDF: {input_path}')
            
            if options['individual_pages']:
                self.stdout.write('🔄 Using individual page signatures...')
                usb_key_signer.sign_each_page_with_usb_key(input_path, output_path)
            else:
                self.stdout.write('🔄 Using standard document signature...')
                usb_key_signer.sign_pdf_with_usb_key(input_path, output_path)
                
            self.stdout.write(self.style.SUCCESS(f'✅ PDF signed successfully: {output_path}'))
            
            # Show file size info
            original_size = os.path.getsize(input_path)
            signed_size = os.path.getsize(output_path)
            self.stdout.write(f'📊 File size: {original_size} → {signed_size} bytes')
            
        finally:
            usb_key_signer.cleanup()

    def sign_batch(self, options):
        """Sign multiple PDF files in a directory."""
        directory = options['sign_batch']
        
        if not os.path.isdir(directory):
            raise CommandError(f'Directory not found: {directory}')
            
        # Find PDF files
        pdf_files = [f for f in os.listdir(directory) if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            self.stdout.write(self.style.WARNING(f'❌ No PDF files found in: {directory}'))
            return
            
        # Initialize USB key
        if not self._initialize_usb_key(options):
            return
            
        try:
            self.stdout.write(f'📁 Batch signing {len(pdf_files)} PDF files...')
            
            signed_count = 0
            for pdf_file in pdf_files:
                input_path = os.path.join(directory, pdf_file)
                base_name = os.path.splitext(pdf_file)[0]
                timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
                output_path = os.path.join(directory, f"{base_name}_usb_signed_{timestamp}.pdf")
                
                try:
                    self.stdout.write(f'🔄 Signing: {pdf_file}')
                    
                    if options['individual_pages']:
                        usb_key_signer.sign_each_page_with_usb_key(input_path, output_path)
                    else:
                        usb_key_signer.sign_pdf_with_usb_key(input_path, output_path)
                        
                    signed_count += 1
                    self.stdout.write(self.style.SUCCESS(f'✅ Signed: {output_path}'))
                    
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'❌ Failed to sign {pdf_file}: {e}'))
                    
            self.stdout.write(self.style.SUCCESS(f'🎉 Batch signing complete: {signed_count}/{len(pdf_files)} files signed'))
            
        finally:
            usb_key_signer.cleanup()

    def show_usb_key_info(self):
        """Show information about connected USB key."""
        info = usb_key_signer.get_usb_key_info()
        
        if info['status'] == 'not_initialized':
            self.stdout.write(self.style.WARNING('❌ No USB key connected'))
            self.stdout.write('Use --sign with proper credentials to connect to a USB key')
            return
            
        if info['status'] == 'error':
            self.stdout.write(self.style.ERROR(f'❌ Error: {info["message"]}'))
            return
            
        self.stdout.write(self.style.SUCCESS('🔑 USB Key Information:'))
        self.stdout.write(f'   Status: {info["status"]}')
        self.stdout.write(f'   Signer: {info["signer_name"]}')
        self.stdout.write(f'   Email: {info["email"]}')
        self.stdout.write(f'   Token: {info["token_label"]}')
        self.stdout.write(f'   Valid from: {info["valid_from"]}')
        self.stdout.write(f'   Valid until: {info["valid_until"]}')
        self.stdout.write(f'   Subject: {info["subject"]}')

    def _initialize_usb_key(self, options):
        """Initialize USB key connection."""
        # Auto-detect if library not specified
        if not options['library']:
            detected_keys = usb_key_manager.detect_usb_keys()
            if not detected_keys:
                self.stdout.write(self.style.ERROR('❌ No USB keys detected'))
                return False
                
            # Use first detected key
            key_info = detected_keys[0]
            library_path = key_info['library_path']
            
            if not key_info.get('tokens'):
                self.stdout.write(self.style.ERROR('❌ No tokens found on USB key'))
                return False
                
            # Use first token if not specified
            if not options['token']:
                token_label = key_info['tokens'][0]['label']
            else:
                token_label = options['token']
        else:
            library_path = options['library']
            token_label = options['token'] or 'Unknown'
            
        # Get PIN
        if options['pin']:
            pin = options['pin']
        else:
            pin = getpass.getpass('🔐 Enter USB key PIN: ')
            
        self.stdout.write(f'🔌 Connecting to USB key: {token_label}')
        
        if not usb_key_signer.initialize_usb_key(library_path, token_label, pin):
            self.stdout.write(self.style.ERROR('❌ Failed to initialize USB key'))
            return False
            
        self.stdout.write(self.style.SUCCESS('✅ USB key connected successfully'))
        return True

    def print_help(self):
        """Print usage help."""
        self.stdout.write(self.style.SUCCESS('🔑 USB Key PDF Signing Tool'))
        self.stdout.write('')
        self.stdout.write('Available operations:')
        self.stdout.write('  --detect                    Detect available USB keys')
        self.stdout.write('  --list-tokens              List tokens on USB keys')
        self.stdout.write('  --sign <file.pdf>          Sign a PDF file')
        self.stdout.write('  --sign-batch <directory>   Sign all PDFs in directory')
        self.stdout.write('  --info                     Show USB key information')
        self.stdout.write('')
        self.stdout.write('Options:')
        self.stdout.write('  --individual-pages         Sign each page individually')
        self.stdout.write('  --output <path>            Output path for signed PDF')
        self.stdout.write('  --library <path>           PKCS#11 library path')
        self.stdout.write('  --token <label>            Token label to use')
        self.stdout.write('  --pin <pin>                USB key PIN')
        self.stdout.write('')
        self.stdout.write('Examples:')
        self.stdout.write('  python manage.py usb_key_sign --detect')
        self.stdout.write('  python manage.py usb_key_sign --sign document.pdf')
        self.stdout.write('  python manage.py usb_key_sign --sign document.pdf --individual-pages')
        self.stdout.write('  python manage.py usb_key_sign --sign-batch /path/to/pdfs/')
