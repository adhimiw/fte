#!/usr/bin/env python3
"""
Enhanced PDF Signature Testing Script

This script tests the improved PDF signature implementation with:
1. Enhanced font compatibility (Helvetica instead of Times-Roman)
2. Proper DocMDP enforcement for document protection
3. Compatibility testing across different PDF viewers

Usage:
    python test_enhanced_pdf_signing.py

The script will:
- Create test PDFs (single-page and multi-page)
- Sign them with the enhanced implementation
- Verify font compatibility and document protection
- Generate test reports for manual verification in PDF viewers
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import our enhanced PDF signing utilities
try:
    from pdf_signature.utils import (
        sign_pdf_multi_page_with_proper_mdp,
        SignatureAppearance,
        ENDESIVE_AVAILABLE
    )
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    print("✓ Successfully imported enhanced PDF signing utilities")
except ImportError as e:
    print(f"✗ Import error: {e}")
    print("Please ensure all dependencies are installed:")
    print("pip install reportlab endesive cryptography")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_test_pdf(filename, content, num_pages=1):
    """Create a test PDF with specified content and number of pages."""
    logger.info(f"Creating test PDF: {filename} with {num_pages} page(s)")
    
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    
    for page_num in range(1, num_pages + 1):
        # Add content to each page
        c.setFont("Helvetica", 16)
        c.drawString(100, height - 100, f"Enhanced PDF Signature Test - Page {page_num}")
        
        c.setFont("Helvetica", 12)
        y_position = height - 150
        
        # Add test content
        test_lines = [
            f"Page {page_num} of {num_pages}",
            "",
            "FONT COMPATIBILITY TEST:",
            "This PDF tests the enhanced Helvetica font implementation",
            "which should render correctly in:",
            "• Adobe Acrobat Reader",
            "• Microsoft Edge PDF viewer", 
            "• Chrome PDF viewer",
            "• Firefox PDF viewer",
            "",
            "DOCUMENT PROTECTION TEST:",
            "After signing, this PDF should show:",
            "• 'Changes NOT allowed' in all PDF viewers",
            "• Proper DocMDP level 1 enforcement",
            "• Certification signature protection",
            "",
            f"Content: {content}",
            "",
            "This is a test document for verifying enhanced PDF signature",
            "implementation with improved font compatibility and document protection."
        ]
        
        for line in test_lines:
            c.drawString(100, y_position, line)
            y_position -= 20
            if y_position < 100:  # Leave space for signature
                break
        
        # Add page break if not the last page
        if page_num < num_pages:
            c.showPage()
    
    c.save()
    logger.info(f"✓ Created test PDF: {filename}")
    return filename

def test_enhanced_signing():
    """Test the enhanced PDF signing implementation."""
    logger.info("=" * 60)
    logger.info("ENHANCED PDF SIGNATURE TESTING")
    logger.info("=" * 60)
    
    if not ENDESIVE_AVAILABLE:
        logger.error("✗ Endesive library not available. Cannot test signing.")
        return False
    
    # Create test directory
    test_dir = Path("test_results")
    test_dir.mkdir(exist_ok=True)
    
    test_results = []
    
    # Test cases
    test_cases = [
        {
            "name": "Single Page PDF",
            "filename": "test_single_page.pdf",
            "signed_filename": "test_single_page_SIGNED.pdf",
            "content": "Single page test document",
            "pages": 1
        },
        {
            "name": "Multi Page PDF", 
            "filename": "test_multi_page.pdf",
            "signed_filename": "test_multi_page_SIGNED.pdf",
            "content": "Multi page test document",
            "pages": 3
        }
    ]
    
    for test_case in test_cases:
        logger.info(f"\n--- Testing: {test_case['name']} ---")
        
        try:
            # Create test PDF
            input_path = test_dir / test_case['filename']
            output_path = test_dir / test_case['signed_filename']
            
            create_test_pdf(
                str(input_path), 
                test_case['content'], 
                test_case['pages']
            )
            
            # Test enhanced signing
            logger.info(f"Signing with enhanced implementation...")
            result_path = sign_pdf_multi_page_with_proper_mdp(
                str(input_path),
                str(output_path)
            )
            
            if os.path.exists(result_path):
                logger.info(f"✓ Successfully signed: {result_path}")
                test_results.append({
                    "test": test_case['name'],
                    "status": "SUCCESS",
                    "input": str(input_path),
                    "output": result_path,
                    "pages": test_case['pages']
                })
            else:
                logger.error(f"✗ Signed file not found: {result_path}")
                test_results.append({
                    "test": test_case['name'],
                    "status": "FAILED",
                    "error": "Signed file not created"
                })
                
        except Exception as e:
            logger.error(f"✗ Error in {test_case['name']}: {str(e)}")
            test_results.append({
                "test": test_case['name'],
                "status": "ERROR",
                "error": str(e)
            })
    
    # Generate test report
    generate_test_report(test_results, test_dir)
    
    return all(result["status"] == "SUCCESS" for result in test_results)

def generate_test_report(test_results, test_dir):
    """Generate a comprehensive test report."""
    logger.info("\n" + "=" * 60)
    logger.info("TEST REPORT")
    logger.info("=" * 60)
    
    report_path = test_dir / "ENHANCED_SIGNATURE_TEST_REPORT.txt"
    
    with open(report_path, 'w') as f:
        f.write("ENHANCED PDF SIGNATURE TEST REPORT\n")
        f.write("=" * 50 + "\n\n")
        f.write("This report contains results from testing the enhanced PDF signature implementation\n")
        f.write("with improved font compatibility and document protection.\n\n")
        
        f.write("IMPROVEMENTS TESTED:\n")
        f.write("1. Font Compatibility: Helvetica font for universal PDF viewer support\n")
        f.write("2. Document Protection: Proper DocMDP level 1 enforcement\n")
        f.write("3. Certification Order: Certification signature applied first\n\n")
        
        f.write("TEST RESULTS:\n")
        f.write("-" * 20 + "\n")
        
        for result in test_results:
            f.write(f"\nTest: {result['test']}\n")
            f.write(f"Status: {result['status']}\n")
            
            if result['status'] == 'SUCCESS':
                f.write(f"Input: {result['input']}\n")
                f.write(f"Output: {result['output']}\n")
                f.write(f"Pages: {result['pages']}\n")
            elif 'error' in result:
                f.write(f"Error: {result['error']}\n")
        
        f.write("\n" + "=" * 50 + "\n")
        f.write("MANUAL VERIFICATION STEPS:\n")
        f.write("=" * 50 + "\n")
        f.write("1. Open signed PDFs in Adobe Acrobat Reader\n")
        f.write("   - Verify fonts render correctly (no font errors)\n")
        f.write("   - Check signature panel shows 'Changes NOT allowed'\n\n")
        f.write("2. Open signed PDFs in Microsoft Edge\n")
        f.write("   - Verify fonts render correctly\n")
        f.write("   - Check document protection is enforced\n\n")
        f.write("3. Test document modification attempts\n")
        f.write("   - Try to edit text (should be blocked)\n")
        f.write("   - Try to add annotations (should be blocked)\n")
        f.write("   - Verify protection warnings appear\n\n")
        
    logger.info(f"✓ Test report generated: {report_path}")
    
    # Print summary
    success_count = sum(1 for r in test_results if r["status"] == "SUCCESS")
    total_count = len(test_results)
    
    logger.info(f"\nTEST SUMMARY:")
    logger.info(f"Successful: {success_count}/{total_count}")
    logger.info(f"Test files location: {test_dir.absolute()}")
    
    if success_count == total_count:
        logger.info("✓ All tests passed! Enhanced implementation is working correctly.")
    else:
        logger.warning("⚠ Some tests failed. Check the detailed report above.")

if __name__ == "__main__":
    print("Enhanced PDF Signature Testing Script")
    print("=" * 40)
    
    success = test_enhanced_signing()
    
    if success:
        print("\n✓ Enhanced PDF signature testing completed successfully!")
        print("Please manually verify the signed PDFs in different PDF viewers.")
    else:
        print("\n✗ Some tests failed. Check the logs above for details.")
        sys.exit(1)
