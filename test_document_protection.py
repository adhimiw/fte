#!/usr/bin/env python3
"""
Test script to verify PDF digital signature document protection enforcement.

This script tests both endesive and PyHanko implementations to ensure that
signed PDFs properly display "Changes NOT allowed" in PDF viewers.

Usage:
    python test_document_protection.py
"""

import os
import sys
import tempfile
import logging
from datetime import datetime

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FTE.settings')

try:
    import django
    django.setup()
    django_available = True
except Exception as e:
    print(f"Django setup failed: {e}")
    print("Running without Django...")
    django_available = False

if django_available:
    from pdf_signature.utils import (
        sign_pdf_multi_page_with_proper_mdp,
        sign_pdf_multi_page,
        sign_pdf_cryptographically,
        ENDESIVE_AVAILABLE
    )
else:
    # Fallback for testing without Django
    print("Testing without Django - creating minimal test functions...")

    def create_minimal_test():
        print("Creating minimal PDF signature test...")
        return True

    ENDESIVE_AVAILABLE = False

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_sample_pdf(output_path):
    """Create a simple sample PDF for testing."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        c = canvas.Canvas(output_path, pagesize=letter)
        
        # Page 1
        c.drawString(100, 750, "SAMPLE INVOICE - Page 1")
        c.drawString(100, 720, "Invoice Number: INV-2025-001")
        c.drawString(100, 690, "Date: 20/06/2025")
        c.drawString(100, 660, "Amount: $8,496.00")
        c.drawString(100, 630, "")
        c.drawString(100, 600, "For FORMTECH ENGINEERING PVT. LTD.")
        c.drawString(100, 570, "Authorised Signatory")
        c.showPage()
        
        # Page 2
        c.drawString(100, 750, "SAMPLE INVOICE - Page 2")
        c.drawString(100, 720, "Terms and Conditions:")
        c.drawString(100, 690, "1. Payment due within 30 days")
        c.drawString(100, 660, "2. Late payment charges apply")
        c.drawString(100, 630, "3. All disputes subject to Chennai jurisdiction")
        c.showPage()
        
        c.save()
        logger.info(f"Created sample PDF: {output_path}")
        return True
        
    except ImportError:
        logger.error("ReportLab not available. Cannot create sample PDF.")
        return False
    except Exception as e:
        logger.error(f"Error creating sample PDF: {e}")
        return False

def test_signature_implementation(input_pdf, implementation_name, sign_function):
    """Test a specific signature implementation."""
    logger.info(f"\n{'='*60}")
    logger.info(f"TESTING: {implementation_name}")
    logger.info(f"{'='*60}")
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_pdf = f"test_signed_{implementation_name.lower().replace(' ', '_')}_{timestamp}.pdf"
    
    try:
        logger.info(f"Input PDF: {input_pdf}")
        logger.info(f"Output PDF: {output_pdf}")
        
        # Sign the PDF
        result_path = sign_function(input_pdf, output_pdf, None)
        
        if os.path.exists(result_path):
            file_size = os.path.getsize(result_path)
            logger.info(f"✅ SUCCESS: Signed PDF created")
            logger.info(f"   File: {result_path}")
            logger.info(f"   Size: {file_size:,} bytes")
            
            # Instructions for manual verification
            logger.info(f"\n📋 MANUAL VERIFICATION REQUIRED:")
            logger.info(f"   1. Open the signed PDF in Microsoft Edge:")
            logger.info(f"      - Right-click → Open with → Microsoft Edge")
            logger.info(f"   2. Check document properties:")
            logger.info(f"      - Right-click → Properties → Security tab")
            logger.info(f"      - Look for 'Changes allowed' or 'Changes NOT allowed'")
            logger.info(f"   3. Open the signed PDF in Adobe Acrobat:")
            logger.info(f"      - Check signature panel for document protection status")
            logger.info(f"      - Verify no font errors are displayed")
            logger.info(f"   4. Expected result: 'Changes NOT allowed'")
            
            return True
        else:
            logger.error(f"❌ FAILED: Signed PDF not created")
            return False
            
    except Exception as e:
        logger.error(f"❌ FAILED: {implementation_name} signing failed: {e}")
        return False

def main():
    """Main test function."""
    logger.info("PDF Digital Signature Document Protection Test")
    logger.info("=" * 60)
    
    # Check if endesive is available
    if not ENDESIVE_AVAILABLE:
        logger.error("❌ Endesive library not available. Please install: pip install endesive")
        return False
    
    # Create sample PDF
    sample_pdf = "test_sample.pdf"
    if not create_sample_pdf(sample_pdf):
        logger.error("❌ Failed to create sample PDF")
        return False
    
    # Test results
    results = []
    
    # Test 1: Improved Endesive Implementation (Certification First)
    logger.info("\n🔧 Testing improved endesive implementation...")
    success = test_signature_implementation(
        sample_pdf,
        "Improved Endesive (Certification First)",
        sign_pdf_multi_page_with_proper_mdp
    )
    results.append(("Improved Endesive", success))
    
    # Test 2: Legacy Endesive Implementation (for comparison)
    logger.info("\n🔧 Testing legacy endesive implementation...")
    success = test_signature_implementation(
        sample_pdf,
        "Legacy Endesive (Certification After)",
        sign_pdf_multi_page
    )
    results.append(("Legacy Endesive", success))
    
    # Test 3: PyHanko Implementation (if available)
    try:
        from pdf_signature.pyhanko_signer import sign_pdf_multi_page_pyhanko
        logger.info("\n🔧 Testing PyHanko implementation...")
        success = test_signature_implementation(
            sample_pdf,
            "PyHanko (Proper DocMDP)",
            sign_pdf_multi_page_pyhanko
        )
        results.append(("PyHanko", success))
    except ImportError:
        logger.warning("⚠️  PyHanko not available, skipping PyHanko test")
        results.append(("PyHanko", "Not Available"))
    
    # Test 4: Default cryptographic function (should use improved implementation)
    logger.info("\n🔧 Testing default cryptographic function...")
    success = test_signature_implementation(
        sample_pdf,
        "Default Cryptographic (Improved)",
        lambda inp, out, usr: sign_pdf_cryptographically(inp, out, usr, use_pyhanko=False)
    )
    results.append(("Default Cryptographic", success))
    
    # Summary
    logger.info(f"\n{'='*60}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*60}")
    
    for implementation, result in results:
        if result == "Not Available":
            status = "⚠️  SKIPPED"
        elif result:
            status = "✅ PASSED"
        else:
            status = "❌ FAILED"
        logger.info(f"{status} {implementation}")
    
    logger.info(f"\n📋 NEXT STEPS:")
    logger.info(f"1. Manually verify each signed PDF in Microsoft Edge and Adobe Acrobat")
    logger.info(f"2. Check that document properties show 'Changes NOT allowed'")
    logger.info(f"3. Verify signature appearance shows correct format:")
    logger.info(f"   - Digitally Signed by ARUL M")
    logger.info(f"   - Date: dd/mm/yyyy")
    logger.info(f"   - Time: HH:MM GMT +5:30")
    logger.info(f"   - Location: Chennai")
    logger.info(f"4. Ensure no font errors in Adobe Acrobat")
    
    # Clean up sample PDF
    try:
        os.remove(sample_pdf)
        logger.info(f"\nCleaned up sample PDF: {sample_pdf}")
    except:
        pass
    
    return True

if __name__ == "__main__":
    main()
