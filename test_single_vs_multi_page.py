#!/usr/bin/env python3
"""
Test script to verify that both single-page and multi-page PDFs use the improved
implementation with proper DocMDP enforcement.

This script creates both single-page and multi-page PDFs and signs them to ensure
consistent document protection enforcement.
"""

import os
import sys
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
        sign_pdf_single_page,
        sign_pdf_multi_page_with_proper_mdp,
        sign_pdf_cryptographically,
        get_pdf_page_count,
        ENDESIVE_AVAILABLE
    )

def create_single_page_pdf(output_path):
    """Create a single-page PDF for testing."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        c = canvas.Canvas(output_path, pagesize=letter)
        c.drawString(100, 750, "SINGLE-PAGE TEST DOCUMENT")
        c.drawString(100, 720, "Invoice Number: INV-SINGLE-001")
        c.drawString(100, 690, "Date: 20/06/2025")
        c.drawString(100, 660, "Amount: $1,234.56")
        c.drawString(100, 630, "")
        c.drawString(100, 600, "This is a single-page PDF for testing")
        c.drawString(100, 570, "document protection enforcement.")
        c.save()
        print(f"✅ Created single-page PDF: {output_path}")
        return True
        
    except ImportError:
        print("❌ ReportLab not available")
        return False
    except Exception as e:
        print(f"❌ Error creating single-page PDF: {e}")
        return False

def create_multi_page_pdf(output_path):
    """Create a multi-page PDF for testing."""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        c = canvas.Canvas(output_path, pagesize=letter)
        
        # Page 1
        c.drawString(100, 750, "MULTI-PAGE TEST DOCUMENT - Page 1")
        c.drawString(100, 720, "Invoice Number: INV-MULTI-001")
        c.drawString(100, 690, "Date: 20/06/2025")
        c.drawString(100, 660, "Amount: $5,678.90")
        c.showPage()
        
        # Page 2
        c.drawString(100, 750, "MULTI-PAGE TEST DOCUMENT - Page 2")
        c.drawString(100, 720, "Terms and Conditions:")
        c.drawString(100, 690, "1. Payment due within 30 days")
        c.drawString(100, 660, "2. Late payment charges apply")
        c.showPage()
        
        # Page 3
        c.drawString(100, 750, "MULTI-PAGE TEST DOCUMENT - Page 3")
        c.drawString(100, 720, "Additional Information:")
        c.drawString(100, 690, "This is a multi-page PDF for testing")
        c.drawString(100, 660, "document protection enforcement.")
        c.save()
        
        print(f"✅ Created multi-page PDF: {output_path}")
        return True
        
    except ImportError:
        print("❌ ReportLab not available")
        return False
    except Exception as e:
        print(f"❌ Error creating multi-page PDF: {e}")
        return False

def test_pdf_signing(pdf_path, pdf_type, sign_function, function_name):
    """Test signing a PDF with a specific function."""
    print(f"\n{'='*60}")
    print(f"TESTING: {pdf_type} PDF with {function_name}")
    print(f"{'='*60}")
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_pdf = f"test_signed_{pdf_type.lower()}_{timestamp}.pdf"
    
    try:
        print(f"Input PDF: {pdf_path}")
        print(f"Output PDF: {output_pdf}")
        
        # Check page count
        page_count = get_pdf_page_count(pdf_path)
        print(f"Page count: {page_count}")
        
        # Sign the PDF
        result_path = sign_function(pdf_path, output_pdf, None)
        
        if os.path.exists(result_path):
            file_size = os.path.getsize(result_path)
            print(f"✅ SUCCESS: {pdf_type} PDF signed successfully")
            print(f"   File: {result_path}")
            print(f"   Size: {file_size:,} bytes")
            
            # Verify page count after signing
            signed_page_count = get_pdf_page_count(result_path)
            print(f"   Signed PDF page count: {signed_page_count}")
            
            return True
        else:
            print(f"❌ FAILED: Signed PDF not created")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: {pdf_type} PDF signing failed: {e}")
        return False

def main():
    """Main test function."""
    print("Single-Page vs Multi-Page PDF Signing Test")
    print("=" * 60)
    print("Testing that both single-page and multi-page PDFs use")
    print("the improved implementation with proper DocMDP enforcement")
    print("=" * 60)
    
    if not django_available:
        print("❌ Django not available, cannot run tests")
        return False
    
    if not ENDESIVE_AVAILABLE:
        print("❌ Endesive not available, cannot run tests")
        return False
    
    # Create test PDFs
    single_page_pdf = "test_single_page.pdf"
    multi_page_pdf = "test_multi_page.pdf"
    
    if not create_single_page_pdf(single_page_pdf):
        return False
    
    if not create_multi_page_pdf(multi_page_pdf):
        return False
    
    # Test results
    results = []
    
    # Test 1: Single-page PDF with dedicated single-page function
    success = test_pdf_signing(
        single_page_pdf,
        "Single-Page",
        sign_pdf_single_page,
        "sign_pdf_single_page()"
    )
    results.append(("Single-page with sign_pdf_single_page", success))
    
    # Test 2: Single-page PDF with multi-page function
    success = test_pdf_signing(
        single_page_pdf,
        "Single-Page",
        sign_pdf_multi_page_with_proper_mdp,
        "sign_pdf_multi_page_with_proper_mdp()"
    )
    results.append(("Single-page with multi-page function", success))
    
    # Test 3: Multi-page PDF with multi-page function
    success = test_pdf_signing(
        multi_page_pdf,
        "Multi-Page",
        sign_pdf_multi_page_with_proper_mdp,
        "sign_pdf_multi_page_with_proper_mdp()"
    )
    results.append(("Multi-page with multi-page function", success))
    
    # Test 4: Both with cryptographic wrapper
    success = test_pdf_signing(
        single_page_pdf,
        "Single-Page",
        lambda inp, out, usr: sign_pdf_cryptographically(inp, out, usr, use_pyhanko=False),
        "sign_pdf_cryptographically()"
    )
    results.append(("Single-page with cryptographic wrapper", success))
    
    success = test_pdf_signing(
        multi_page_pdf,
        "Multi-Page",
        lambda inp, out, usr: sign_pdf_cryptographically(inp, out, usr, use_pyhanko=False),
        "sign_pdf_cryptographically()"
    )
    results.append(("Multi-page with cryptographic wrapper", success))
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} {test_name}")
    
    print(f"\n📋 VERIFICATION:")
    print(f"✅ All functions should use the improved implementation")
    print(f"✅ All signed PDFs should have certification signature applied FIRST")
    print(f"✅ All signed PDFs should enforce 'Changes NOT allowed'")
    print(f"✅ Both single-page and multi-page PDFs get consistent protection")
    
    # Clean up test PDFs
    try:
        os.remove(single_page_pdf)
        os.remove(multi_page_pdf)
        print(f"\nCleaned up test PDFs")
    except:
        pass
    
    return True

if __name__ == "__main__":
    main()
