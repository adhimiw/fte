#!/usr/bin/env python3
"""
Simple PDF creation test to verify ReportLab functionality.
"""

import os
import sys
from datetime import datetime

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
        print(f"✅ Created sample PDF: {output_path}")
        return True
        
    except ImportError as e:
        print(f"❌ ReportLab not available: {e}")
        print("Please install: pip install reportlab")
        return False
    except Exception as e:
        print(f"❌ Error creating sample PDF: {e}")
        return False

def main():
    """Main test function."""
    print("Simple PDF Creation Test")
    print("=" * 40)
    
    # Create sample PDF
    sample_pdf = "sample.pdf"
    if create_sample_pdf(sample_pdf):
        file_size = os.path.getsize(sample_pdf)
        print(f"✅ SUCCESS: Sample PDF created")
        print(f"   File: {sample_pdf}")
        print(f"   Size: {file_size:,} bytes")
        
        print(f"\n📋 Next Steps:")
        print(f"1. Use Django management command to test signing:")
        print(f"   python manage.py test_pdf_signing --input {sample_pdf}")
        print(f"2. Or test with specific implementations:")
        print(f"   python manage.py test_pdf_signing --input {sample_pdf} --verify")
        
        return True
    else:
        print("❌ Failed to create sample PDF")
        return False

if __name__ == "__main__":
    main()
