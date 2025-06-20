#!/usr/bin/env python3
"""
Document Protection Verification Script

This script helps verify that PDF digital signatures properly enforce document protection.
It provides instructions for manual testing in PDF viewers.
"""

import os
import glob
from datetime import datetime

def find_signed_pdfs():
    """Find all signed PDF files in the current directory."""
    patterns = [
        "django_signed_*.pdf",
        "*_signed_*.pdf", 
        "signed_*.pdf"
    ]
    
    signed_pdfs = []
    for pattern in patterns:
        signed_pdfs.extend(glob.glob(pattern))
    
    return sorted(signed_pdfs)

def analyze_pdf_basic_info(pdf_path):
    """Get basic information about a PDF file."""
    try:
        file_size = os.path.getsize(pdf_path)
        mod_time = datetime.fromtimestamp(os.path.getmtime(pdf_path))
        
        # Check PDF header
        with open(pdf_path, 'rb') as f:
            header = f.read(8)
            is_valid_pdf = header.startswith(b'%PDF-')
        
        return {
            'size': file_size,
            'modified': mod_time,
            'valid_pdf': is_valid_pdf,
            'header': header.decode('ascii', errors='ignore') if is_valid_pdf else 'Invalid'
        }
    except Exception as e:
        return {'error': str(e)}

def print_manual_verification_instructions(pdf_files):
    """Print detailed instructions for manual verification."""
    print("\n" + "="*80)
    print("MANUAL VERIFICATION INSTRUCTIONS")
    print("="*80)
    
    print("\n🔍 CRITICAL TEST: Document Protection Enforcement")
    print("-" * 50)
    
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"\n📄 TEST {i}: {pdf_file}")
        print(f"   File size: {analyze_pdf_basic_info(pdf_file).get('size', 'Unknown'):,} bytes")
        
        print(f"\n   🌐 MICROSOFT EDGE TEST:")
        print(f"   1. Right-click '{pdf_file}' → Open with → Microsoft Edge")
        print(f"   2. Right-click in PDF → Properties → Security tab")
        print(f"   3. Look for document permissions")
        print(f"   4. ✅ EXPECTED: 'Changes NOT allowed' or similar restrictive message")
        print(f"   5. ❌ PROBLEM: 'Changes allowed: Signing*, Form filling*, Commenting*'")
        
        print(f"\n   📖 ADOBE ACROBAT TEST:")
        print(f"   1. Open '{pdf_file}' in Adobe Acrobat Reader")
        print(f"   2. Check signature panel (left side or bottom)")
        print(f"   3. Click on any signature → Properties")
        print(f"   4. ✅ EXPECTED: DocMDP level 1 or 'No changes allowed'")
        print(f"   5. ✅ EXPECTED: No font errors or warnings")
        print(f"   6. ✅ EXPECTED: Signature appearance shows:")
        print(f"      - Digitally Signed by ARUL M")
        print(f"      - Date: dd/mm/yyyy format")
        print(f"      - Time: HH:MM GMT +5:30")
        print(f"      - Location: Chennai")
        
        print(f"\n   🔧 OTHER PDF VIEWERS (Optional):")
        print(f"   - Test in Firefox PDF viewer")
        print(f"   - Test in Chrome PDF viewer")
        print(f"   - Test in other PDF software")

def print_troubleshooting_guide():
    """Print troubleshooting guide for common issues."""
    print("\n" + "="*80)
    print("TROUBLESHOOTING GUIDE")
    print("="*80)
    
    print("\n❌ PROBLEM: 'Changes allowed' instead of 'Changes NOT allowed'")
    print("   CAUSE: Certification signature not properly enforced")
    print("   SOLUTION: Use improved implementation with certification signature applied FIRST")
    print("   CODE: sign_pdf_multi_page_with_proper_mdp() or PyHanko implementation")
    
    print("\n❌ PROBLEM: Font errors in Adobe Acrobat")
    print("   CAUSE: Font compatibility issues")
    print("   SOLUTION: Current Times-Roman font with signature_manual should resolve this")
    print("   STATUS: Should be fixed in current implementation")
    
    print("\n❌ PROBLEM: Signature not visible")
    print("   CAUSE: Signature box positioning or appearance issues")
    print("   SOLUTION: Check signature box coordinates and appearance configuration")
    
    print("\n❌ PROBLEM: Certificate validation errors")
    print("   CAUSE: Self-signed certificate not trusted")
    print("   SOLUTION: This is expected for testing - focus on document protection")

def main():
    """Main verification function."""
    print("PDF Document Protection Verification Tool")
    print("="*50)
    print(f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"Location: Chennai")
    
    # Find signed PDFs
    signed_pdfs = find_signed_pdfs()
    
    if not signed_pdfs:
        print("\n❌ No signed PDF files found in current directory.")
        print("\nTo create test PDFs, run:")
        print("   python simple_pdf_test.py")
        print("   python manage.py test_pdf_signing --input sample.pdf")
        return
    
    print(f"\n✅ Found {len(signed_pdfs)} signed PDF file(s):")
    for pdf in signed_pdfs:
        info = analyze_pdf_basic_info(pdf)
        print(f"   📄 {pdf}")
        print(f"      Size: {info.get('size', 'Unknown'):,} bytes")
        print(f"      Modified: {info.get('modified', 'Unknown')}")
        print(f"      Valid PDF: {info.get('valid_pdf', False)}")
    
    # Print verification instructions
    print_manual_verification_instructions(signed_pdfs)
    
    # Print troubleshooting guide
    print_troubleshooting_guide()
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print("1. Test each signed PDF in Microsoft Edge and Adobe Acrobat")
    print("2. Verify 'Changes NOT allowed' is displayed")
    print("3. Check signature appearance and font rendering")
    print("4. Report any issues found")
    print("\n✅ If all tests pass, document protection is properly enforced!")
    print("❌ If tests fail, check troubleshooting guide above")

if __name__ == "__main__":
    main()
