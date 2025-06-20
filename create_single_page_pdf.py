#!/usr/bin/env python3
"""
Create a single-page PDF for testing.
"""

import os

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

def main():
    """Main function."""
    print("Creating Single-Page PDF Test")
    print("=" * 40)
    
    single_page_pdf = "single_page_test.pdf"
    if create_single_page_pdf(single_page_pdf):
        file_size = os.path.getsize(single_page_pdf)
        print(f"✅ SUCCESS: Single-page PDF created")
        print(f"   File: {single_page_pdf}")
        print(f"   Size: {file_size:,} bytes")
        
        print(f"\n📋 Next Steps:")
        print(f"1. Test single-page PDF signing:")
        print(f"   python manage.py test_pdf_signing --input {single_page_pdf}")
        print(f"2. Compare with multi-page PDF signing:")
        print(f"   python manage.py test_pdf_signing --input sample.pdf")
        
        return True
    else:
        print("❌ Failed to create single-page PDF")
        return False

if __name__ == "__main__":
    main()
