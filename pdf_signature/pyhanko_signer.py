#!/usr/bin/env python3
"""
PyHanko PDF Signing Integration
Alternative PDF signing implementation using PyHanko library
"""

import os
import logging
import pytz
from datetime import datetime
from io import BytesIO

try:
    from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign import signers
    from pyhanko.sign.fields import SigSeedSubFilter
    from pyhanko.sign.signers.pdf_signer import (
        PdfSignatureMetadata,
        SigMDPPerm,
        PdfSigner,
    )
    from pyhanko.sign.signers.signing_commons import SigningError
    from pyhanko.pdf_utils.config import TextStampStyle, TextBoxStyle
    from pyhanko.pdf_utils.layout import BoxSpecification
    from pyhanko.sign.validation.errors import SignatureValidationError
    from pyhanko.sign.validation import validate_pdf_signature
    from pyhanko.keys.pkcs12 import load_pkcs12
    PYHANKO_AVAILABLE = True
except ImportError:
    PYHANKO_AVAILABLE = False

logger = logging.getLogger(__name__)

# Configuration
SIGNATURE_REASON = "Document Certified: No changes allowed after this signature."
SIGNATURE_LOCATION = "Chennai"
TIMEZONE = "Asia/Kolkata"  # IANA timezone name for GMT+5:30
SIGNER_NAME = "ARUL M"

def ensure_directories_exist(file_path):
    """Ensure directory exists for the given file path."""
    dir_name = os.path.dirname(file_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

def get_certificate_info_pyhanko(cert_path, password):
    """Load certificate and create PyHanko signer."""
    if not PYHANKO_AVAILABLE:
        raise ImportError("PyHanko library is not available")
    
    try:
        pfx_res = load_pkcs12(cert_path, password)
        signer = signers.SimpleSigner(
            pfx_res.key_handle, 
            pfx_res.cert_registry, 
            signature_mechanism=None
        )
        logger.info(f"Loaded certificate and key for: {str(signer.signing_cert.subject)}")
        return signer
    except Exception as e:
        logger.error(f"Error loading certificate from {cert_path}: {e}", exc_info=True)
        raise

def sign_pdf_pyhanko_with_proper_mdp(input_pdf_path, output_pdf_path, cert_path, cert_password, user=None):
    """
    Sign PDF using PyHanko with proper DocMDP enforcement for document protection.

    This implementation creates a certification signature with DocMDP level 1 (NO CHANGES ALLOWED)
    followed by visible approval signatures on each page. The certification signature properly
    enforces document protection that should display "Changes NOT allowed" in PDF viewers.

    Args:
        input_pdf_path (str): Path to input PDF
        output_pdf_path (str): Path to output signed PDF
        cert_path (str): Path to PKCS#12 certificate
        cert_password (str): Certificate password
        user: Django user object (optional)

    Returns:
        str: Path to signed PDF
    """
    if not PYHANKO_AVAILABLE:
        raise ImportError("PyHanko library is not available. Please install: pip install pyHanko")

    ensure_directories_exist(output_pdf_path)
    
    try:
        # Get certificate signer
        signer = get_certificate_info_pyhanko(cert_path, cert_password)
        
        # Create approval output buffer
        approval_output_buffer = BytesIO()

        # CRITICAL FIX: Apply Certification Signature FIRST (not last) to properly enforce DocMDP
        logger.info("STEP 1: Applying certification signature FIRST with DocMDP level 1 (NO CHANGES ALLOWED)...")

        # Read input PDF and get page count
        with open(input_pdf_path, "rb") as pdf_file:
            pdf_data = pdf_file.read()

        r = PdfFileReader(BytesIO(pdf_data))
        pages_ref = r.root.get("/Pages")
        if not pages_ref:
            raise ValueError("Could not find /Pages node in PDF root.")
        pages_node = r.get_object(pages_ref.reference)
        if not isinstance(pages_node, dict) or "/Count" not in pages_node:
            raise ValueError("Could not determine page count from /Pages dictionary.")
        num_pages = pages_node["/Count"]
        logger.info(f"Found {num_pages} pages in the document.")

        # Apply invisible certification signature first
        w_certified = IncrementalPdfFileWriter(BytesIO(pdf_data))

        cert_meta = PdfSignatureMetadata(
            field_name="CertificationSignature",
            certify=True,
            docmdp_permissions=SigMDPPerm.NO_CHANGES,  # DocMDP level 1 - NO CHANGES ALLOWED
            subfilter=SigSeedSubFilter.ADOBE_PKCS7_DETACHED,
            # Remove reason as per requirements
            location=SIGNATURE_LOCATION,
        )

        # Apply certification signature (invisible)
        w_certified = signers.sign_pdf(
            w_certified,
            cert_meta,
            signer=signer,
            certify=True,  # This is the key - certification signature
        )
        logger.info("Certification signature applied with DocMDP level 1 (NO CHANGES ALLOWED)")

        # Get the certified PDF data
        certified_pdf_data = w_certified.getvalue()

        # STEP 2: Now apply visible approval signatures to each page
        logger.info("STEP 2: Applying visible approval signatures to each page...")

        # Define text styles
        style_line1 = TextBoxStyle(font_size=10)
        style_line2 = TextBoxStyle(font_size=12)  # Bold (Note: weight parameter not supported)
        style_line3 = TextBoxStyle(font_size=10)
        style_line4 = TextBoxStyle(font_size=10)

        current_pdf_data = certified_pdf_data

        for i in range(num_pages):
            page_num = i + 1
            field_name = f"ApprovalSignaturePage{page_num}"
            logger.info(f"Signing page {page_num} with field {field_name}")

            now_local = datetime.now(pytz.timezone(TIMEZONE))
            # Format date as dd/mm/yyyy (e.g., "20/06/2025")
            date_str = now_local.strftime("%d/%m/%Y")
            # Format time as HH:MM GMT +5:30 (e.g., "11:44 GMT +5:30")
            time_str = now_local.strftime("%H:%M GMT +5:30")

            meta = PdfSignatureMetadata(
                field_name=field_name,
                location=SIGNATURE_LOCATION,
                # Remove reason as per requirements
                page=i,  # Page index is 0-based
                box=(450, 50, 580, 120)  # Same position as endesive implementation
            )

            # Define the text stamp appearance with new format
            text_box_spec = BoxSpecification(
                width=130, height=70
            )
            stamp_style = TextStampStyle(
                stamp_text=(
                    f"{SIGNER_NAME}\n"
                    f"Date: {date_str}\n"
                    f"Time: {time_str}\n"
                    f"Location: {SIGNATURE_LOCATION}"
                ),
                text_box_style=style_line1,  # Default style
                text_box_spec=text_box_spec,
            )

            # Create incremental writer from current PDF data
            w_approval = IncrementalPdfFileWriter(BytesIO(current_pdf_data))

            w_approval = signers.sign_pdf(
                w_approval,
                meta,
                signer=signer,
                stamp_style=stamp_style,
                certify=False,  # This is an approval signature, not certification
            )
            logger.info(f"Applied approval signature to page {page_num}")

            # Update current PDF data for next iteration
            current_pdf_data = w_approval.getvalue()

        # Save final result
        with open(output_pdf_path, "wb") as doc_out:
            doc_out.write(current_pdf_data)

        logger.info(f"Final PDF with proper DocMDP enforcement saved to {output_pdf_path}")
        logger.info("CRITICAL: Certification signature was applied FIRST to ensure proper document protection")
        
        return output_pdf_path

    except SigningError as e:
        logger.error(f"PyHanko signing error: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred during PyHanko signing: {e}", exc_info=True)
        raise

def verify_pdf_signature_pyhanko(pdf_path):
    """
    Verify PDF signatures using PyHanko.
    
    Args:
        pdf_path (str): Path to PDF file to verify
        
    Returns:
        list: List of verification results
    """
    if not PYHANKO_AVAILABLE:
        logger.warning("PyHanko not available, cannot verify PDF signatures.")
        return []
    
    results = []
    logger.info(f"Verifying signatures in {pdf_path} using PyHanko")
    
    try:
        with open(pdf_path, "rb") as f:
            embedded_sig_info = signers.embedded_signatures(f)
            logger.info(f"Found {len(embedded_sig_info)} embedded signature objects.")
            
            for i, sig_obj in enumerate(embedded_sig_info):
                logger.info(f"--- Verifying Signature {i+1} ({sig_obj.field_name}) ---")
                try:
                    validation_status = validate_pdf_signature(sig_obj)
                    
                    result = {
                        'signature_name': sig_obj.field_name,
                        'valid': validation_status.valid,
                        'trusted': validation_status.trusted,
                        'modification_level': str(validation_status.modification_level),
                        'summary': validation_status.summary,
                        'errors': [str(err) for err in validation_status.errors] if validation_status.errors else [],
                        'warnings': [str(warn) for warn in validation_status.warnings] if validation_status.warnings else []
                    }
                    
                    results.append((sig_obj.field_name, validation_status.valid, result))
                    
                    logger.info(f"Signature {i+1} Validation Status: {validation_status.valid}")
                    logger.info(f"Trust Status: {validation_status.trusted}")
                    logger.info(f"Modification Level: {validation_status.modification_level}")
                    logger.info(f"Summary: {validation_status.summary}")
                    
                    if validation_status.trusted:
                        logger.info("Signature is trusted.")
                    else:
                        logger.warning("Signature is NOT trusted (likely self-signed or untrusted CA).")
                    if validation_status.valid:
                        logger.info("Signature is cryptographically valid.")
                    else:
                        logger.error("Signature is cryptographically INVALID.")
                    if validation_status.errors:
                        for err in validation_status.errors:
                            logger.error(f"Validation Error: {err}")
                    if validation_status.warnings:
                        for warn in validation_status.warnings:
                            logger.warning(f"Validation Warning: {warn}")
                            
                except SignatureValidationError as e:
                    logger.error(f"Signature {i+1} validation failed: {e}")
                    results.append((sig_obj.field_name, False, {'error': str(e)}))
                except Exception as e:
                    logger.error(f"Error during validation of signature {i+1}: {e}", exc_info=True)
                    results.append((sig_obj.field_name, False, {'error': str(e)}))
                    
    except Exception as e:
        logger.error(f"Error reading or verifying PDF with PyHanko: {e}", exc_info=True)
    
    return results

def sign_pdf_multi_page_pyhanko(input_path, output_path, user=None):
    """
    PyHanko wrapper that matches the signature of the main signing function.
    
    Args:
        input_path (str): Path to input PDF
        output_path (str): Path to output PDF
        user: Django user object (optional)
        
    Returns:
        str: Path to signed PDF
    """
    # Get certificate configuration
    from .utils import CERTIFICATE_P12_PATH, CERTIFICATE_PASSWORD
    
    if isinstance(CERTIFICATE_PASSWORD, bytes):
        cert_password = CERTIFICATE_PASSWORD.decode('utf-8')
    else:
        cert_password = CERTIFICATE_PASSWORD
    
    return sign_pdf_pyhanko_with_proper_mdp(input_path, output_path, CERTIFICATE_P12_PATH, cert_password, user)
