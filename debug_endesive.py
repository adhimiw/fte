#!/usr/bin/env python3
"""
Debug endesive output to understand the correct format.
"""

import os
import sys
sys.path.append('.')

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'digital_workspace.settings')
import django
django.setup()

from pdf_signature.utils import (
    ensure_certificate_exists, 
    ENDESIVE_AVAILABLE, 
    endesive_cms,
    create_signature_config_for_user,
    build_signature_appearance,
    CERTIFICATE_CONFIG
)
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat import backends
from django.utils import timezone
from datetime import timezone as dt_timezone, timedelta

def debug_endesive_signing():
    """Debug the endesive signing process step by step."""
    
    if not ENDESIVE_AVAILABLE:
        print("Endesive not available")
        return
    
    # Load certificate
    cert_path = ensure_certificate_exists()
    print(f"Certificate path: {cert_path}")
    
    # Load PKCS#12 certificate
    with open(cert_path, 'rb') as cert_file:
        cert_data = cert_file.read()
    
    # Try different passwords
    passwords = [b"digital_workspace_2024", b"arul_personal_2024", None, b""]
    p12 = None
    
    for password in passwords:
        try:
            p12 = pkcs12.load_key_and_certificates(cert_data, password, backends.default_backend())
            print(f"Certificate loaded with password: {'[password]' if password else '[no password]'}")
            break
        except Exception as e:
            continue
    
    if not p12:
        print("Failed to load certificate")
        return
    
    # Read test PDF
    with open('test_sample.pdf', 'rb') as pdf_file:
        pdf_data = pdf_file.read()
    
    print(f"Original PDF size: {len(pdf_data)} bytes")
    print(f"Original PDF header: {pdf_data[:20]}")
    
    # Create signature configuration
    current_time = timezone.now()
    chennai_time = current_time.astimezone(dt_timezone(timedelta(hours=5, minutes=30)))
    
    signature_config = create_signature_config_for_user(None, "standard")
    signature_manual = build_signature_appearance(signature_config, chennai_time, CERTIFICATE_CONFIG['common_name'])
    
    # Simple signature dictionary
    signature_dict = {
        "sigflags": 3,
        "sigflagsft": 132,
        "sigpage": 0,
        "sigfield": "Signature1",
        "auto_sigfield": True,
        "signaturebox": (450, 50, 580, 120),
        "signature": f"Digitally signed by {CERTIFICATE_CONFIG['common_name']}",
        "reason": "Document authentication and integrity verification",
        "location": "Chennai, Tamil Nadu, India",
        "contact": CERTIFICATE_CONFIG['email'],
        "signingdate": chennai_time.strftime("D:%Y%m%d%H%M%S+05'30'"),
        "signature_manual": signature_manual,
        "aligned": 0,
    }
    
    print(f"Signature dictionary keys: {list(signature_dict.keys())}")
    
    # Sign with endesive
    try:
        signed_data = endesive_cms.sign(
            pdf_data,
            signature_dict,
            p12[0],  # private key
            p12[1],  # certificate
            p12[2] or [],  # additional certificates
            "sha256"
        )
        
        print(f"Signed data size: {len(signed_data)} bytes")
        print(f"Signed data header: {signed_data[:50]}")
        
        # Write to file
        with open('debug_signed.pdf', 'wb') as f:
            f.write(signed_data)
        
        print("Debug signed PDF written to debug_signed.pdf")
        
        # Test if it's a valid PDF
        try:
            import PyPDF2
            with open('debug_signed.pdf', 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                print(f"Debug PDF is valid! Pages: {len(reader.pages)}")
        except Exception as e:
            print(f"Debug PDF validation failed: {e}")
            
    except Exception as e:
        print(f"Endesive signing failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_endesive_signing()
