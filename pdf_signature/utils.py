#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Cryptographic utilities for PDF digital signatures.

This module provides enhanced cryptographic digital signature functionality
using X.509 certificates and the endesive library, addressing multi-page signing,
trusted certificate validation, document protection, and PDF/A considerations.
"""

import os
import logging
import tempfile
import shutil
from datetime import datetime, timezone as dt_timezone, timedelta
from typing import List, Dict, Optional, Tuple

# Third-party libraries
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat import backends
from PyPDF2 import PdfReader, PdfWriter

# Django specific (optional, adapt if not in Django context)
try:
    from django.conf import settings
    from django.utils import timezone
    DJANGO_AVAILABLE = True
except ImportError:
    settings = None
    timezone = None
    DJANGO_AVAILABLE = False

# Set up logging
logger = logging.getLogger(__name__)

# --- Configuration --- #

# IMPORTANT: Configure these paths and password securely
# Use environment variables, Django settings, or a config file in production

# Simple fallback configuration
CERTIFICATE_P12_PATH = os.environ.get("PDF_SIGN_CERT_PATH",
                                     os.path.join(os.getcwd(), "certificates", "signing_cert.p12"))
CERTIFICATE_PASSWORD = os.environ.get("PDF_SIGN_CERT_PASSWORD", "digital_workspace_2024").encode("utf-8")
CERTIFICATE_DIR = os.path.dirname(CERTIFICATE_P12_PATH)

# Ensure certificate directory exists
os.makedirs(CERTIFICATE_DIR, exist_ok=True)

# Default Signer Info (extracted from certificate if possible, fallback to this)
DEFAULT_SIGNER_INFO = {
    'common_name': 'ARUL M',
    'organization': 'PERSONAL',
    'organizational_unit': 'Individual',
    'country': 'IN',
    'state': 'Tamil Nadu',
    'locality': 'Chennai',
    'email': 'm.arul@fte.com',
}

# Timestamp Authority (TSA) URL for LTV (optional but recommended)
# Find a suitable TSA provider
TSA_URL = os.environ.get("PDF_SIGN_TSA_URL", None) # e.g., "http://timestamp.digicert.com"

# --- Endesive Check --- #

try:
    import endesive.pdf.cms as endesive_cms
    from endesive.pdf.verify import verify as endesive_verify_func
    ENDESIVE_AVAILABLE = True
    logger.info("Endesive library loaded successfully.")
except ImportError as e:
    logger.error(f"Endesive library not found or failed to import: {e}. PDF signing functionality is disabled.")
    ENDESIVE_AVAILABLE = False
    endesive_cms = None
    endesive_verify_func = None

# --- Helper Functions --- #

def get_pdf_page_count(pdf_path):
    """Get the number of pages in a PDF file."""
    try:
        reader = PdfReader(pdf_path)
        return len(reader.pages)
    except Exception as e:
        logger.error(f"Error reading PDF page count from {pdf_path}: {e}")
        raise

def load_certificate_data():
    """
    Load the private key, certificate, and certificate chain from the configured PKCS#12 file.

    Returns:
        tuple: (private_key, certificate, additional_certificates) or raises Exception
    """
    if not os.path.exists(CERTIFICATE_P12_PATH):
        logger.error(f"Certificate file not found at configured path: {CERTIFICATE_P12_PATH}")
        logger.error("Please configure CERTIFICATE_P12_PATH and ensure the file exists.")
        raise FileNotFoundError(f"Certificate file not found: {CERTIFICATE_P12_PATH}")

    try:
        with open(CERTIFICATE_P12_PATH, 'rb') as cert_file:
            p12_data = cert_file.read()

        logger.info(f"Loading certificate from: {CERTIFICATE_P12_PATH}")
        private_key, certificate, additional_certificates = serialization.pkcs12.load_key_and_certificates(
            p12_data,
            CERTIFICATE_PASSWORD,
            backends.default_backend()
        )
        logger.info(f"Certificate loaded successfully for subject: {certificate.subject}")
        return private_key, certificate, additional_certificates
    except ValueError as e:
        if "MAC check failed" in str(e) or "decryption failed" in str(e):
            logger.error(f"Incorrect password for certificate file: {CERTIFICATE_P12_PATH}")
            raise ValueError("Incorrect certificate password.") from e
        else:
            logger.error(f"Error loading certificate file {CERTIFICATE_P12_PATH}: {e}")
            raise
    except Exception as e:
        logger.error(f"Unexpected error loading certificate {CERTIFICATE_P12_PATH}: {e}")
        raise

def get_signer_info_from_cert(certificate):
    """Extract signer information from the certificate subject."""
    info = DEFAULT_SIGNER_INFO.copy() # Start with defaults
    try:
        info["common_name"] = certificate.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
        # Add other fields as needed, handling potential missing attributes
        attrs_map = {
            NameOID.ORGANIZATION_NAME: 'organization',
            NameOID.ORGANIZATIONAL_UNIT_NAME: 'organizational_unit',
            NameOID.COUNTRY_NAME: 'country',
            NameOID.STATE_OR_PROVINCE_NAME: 'state',
            NameOID.LOCALITY_NAME: 'locality',
            NameOID.EMAIL_ADDRESS: 'email',
        }
        for oid, key in attrs_map.items():
            attributes = certificate.subject.get_attributes_for_oid(oid)
            if attributes:
                info[key] = attributes[0].value
    except Exception as e:
        logger.warning(f"Could not extract all details from certificate subject: {e}. Using defaults.")
    return info

# --- Signature Appearance Class (Simplified) --- #

class SignatureAppearance:
    """
    Configuration for the visual appearance of the signature with enhanced font compatibility.

    Uses the most universally compatible PDF fonts to ensure proper rendering
    across all PDF viewers including Adobe Acrobat, Microsoft Edge, and others.
    """

    def __init__(self, signer_info):
        self.signer_info = signer_info
        # Signature box coordinates (bottom-right corner typical placement)
        # Values relative to page size might be better, but fixed for now.
        self.box = (450, 50, 580, 120) # (x1, y1, x2, y2)
        self.font_size_normal = 10
        self.font_size_large = 12

        # ENHANCED FONT COMPATIBILITY: Use Helvetica as primary font
        # Helvetica is one of the 14 standard PDF fonts and has better compatibility
        # than Times-Roman in many PDF viewers, especially Adobe Acrobat
        self.font_name = "Helvetica"  # Primary font - most universally compatible
        self.font_name_fallback = "Times-Roman"  # Fallback font if Helvetica fails

        # The 14 standard PDF fonts (guaranteed to be available in all PDF viewers):
        # Helvetica, Helvetica-Bold, Helvetica-Oblique, Helvetica-BoldOblique
        # Times-Roman, Times-Bold, Times-Italic, Times-BoldItalic
        # Courier, Courier-Bold, Courier-Oblique, Courier-BoldOblique
        # Symbol, ZapfDingbats

    def get_compatible_font(self):
        """
        Get the most compatible font for PDF signatures.

        Returns the primary font (Helvetica) which has the best compatibility
        across all PDF viewers including Adobe Acrobat.

        Returns:
            str: Font name to use for signature appearance
        """
        # Helvetica is the most universally compatible of the 14 standard PDF fonts
        # It renders consistently across Adobe Acrobat, Microsoft Edge, and other viewers
        return self.font_name

    def build_appearance_dict(self, page_num):
        """
        Build the appearance dictionary for endesive for a specific page.
        Uses the required 4-line format with custom formatting:
        - Line 1: "Digitally Signed by ARUL M" (with ARUL M in bold)
        - Line 2: "Date: dd/mm/yyyy"
        - Line 3: "Time: HH:MM GMT (Chennai)"
        - Line 4: "Location: Chennai"
        """
        current_time = datetime.now(dt_timezone.utc)
        # Use Chennai timezone (+05:30)
        chennai_tz = dt_timezone(timedelta(hours=5, minutes=30))
        chennai_time = current_time.astimezone(chennai_tz)

        # Format date as dd/mm/yyyy (e.g., "20/06/2025")
        date_str = chennai_time.strftime("%d/%m/%Y")

        # Format time as HH:MM GMT +5:30 (e.g., "11:44 GMT +5:30")
        time_str = chennai_time.strftime("%H:%M GMT +5:30")

        signer_name = self.signer_info.get('common_name', 'Unknown Signer').upper()
        location = self.signer_info.get('locality', 'Chennai')

        # Calculate text positions within the box (y from bottom)
        box_height = self.box[3] - self.box[1]
        line_spacing = 15
        x_offset = 5
        y_line4 = 10 # Bottom line
        y_line3 = y_line4 + line_spacing
        y_line2 = y_line3 + line_spacing
        y_line1 = y_line2 + line_spacing

        # ENHANCED FONT COMPATIBILITY: Use signature_manual for precise font control
        # This method gives us direct control over fonts and avoids automatic font selection
        # Using Helvetica as primary font for better Adobe Acrobat compatibility
        appearance = {
            # Basic metadata - required by endesive
            "location": location,
            "contact": self.signer_info.get('email', ''),
            "signingdate": chennai_time.strftime("D:%Y%m%d%H%M%S+05'30'"), # Required by endesive

            # Use signature_manual for precise control over fonts and layout
            # CRITICAL: Using Helvetica font for maximum compatibility across all PDF viewers
            "signature_manual": [
                ['fill_colour', 0, 0, 0],  # Black text
                # Line 1: Signer name in bold (removed "Digitally Signed by" prefix)
                ['text_box', f'{signer_name}', self.get_compatible_font(), x_offset, y_line1,
                 self.box[2]-self.box[0]-x_offset*2, 15, self.font_size_large, True, 'left', 'top'],
                # Line 2: "Date: dd/mm/yyyy"
                ['text_box', f'Date: {date_str}', self.get_compatible_font(), x_offset, y_line2,
                 self.box[2]-self.box[0]-x_offset*2, 12, self.font_size_normal, True, 'left', 'top'],
                # Line 3: "Time: HH:MM GMT +5:30"
                ['text_box', f'Time: {time_str}', self.get_compatible_font(), x_offset, y_line3,
                 self.box[2]-self.box[0]-x_offset*2, 12, self.font_size_normal, True, 'left', 'top'],
                # Line 4: "Location: Chennai"
                ['text_box', f'Location: {location}', self.get_compatible_font(), x_offset, y_line4,
                 self.box[2]-self.box[0]-x_offset*2, 12, self.font_size_normal, True, 'left', 'top'],
            ],
        }
        return appearance

# --- Core Signing Logic --- #

def sign_pdf_multi_page_with_proper_mdp(input_path, output_path, user=None):
    """
    Signs PDF documents with ENHANCED font compatibility and proper DocMDP enforcement.

    CRITICAL IMPROVEMENTS:
    1. FONT COMPATIBILITY: Uses Helvetica font (most universally compatible) instead of Times-Roman
    2. DOCUMENT PROTECTION: Applies certification signature FIRST with DocMDP level 1
    3. UNIVERSAL SUPPORT: Works across Adobe Acrobat, Microsoft Edge, and other PDF viewers

    This function addresses two major issues:
    - Font rendering errors in Adobe Acrobat (solved by using Helvetica)
    - Document protection not enforced properly (solved by proper certification order)

    The enhanced process:
    1. Apply CERTIFICATION signature first with DocMDP level 1 (NO CHANGES ALLOWED)
    2. Use Helvetica font for maximum compatibility across all PDF viewers
    3. Apply visible approval signatures with enhanced font rendering
    4. Ensure "Changes NOT allowed" is displayed in all PDF viewers

    Args:
        input_path (str): Path to the input PDF file (single-page or multi-page).
        output_path (str): Path to save the final signed PDF file.
        user: Django user object (optional, for logging).

    Returns:
        str: Path to the signed PDF file.

    Raises:
        Exception: If endesive is not available or signing fails.
        FileNotFoundError: If the certificate file is not found.
        ValueError: If the certificate password is incorrect.
    """
    if not ENDESIVE_AVAILABLE:
        raise Exception("Endesive library is required for PDF signing.")

    logger.info(f"Starting ENHANCED PDF signing with font compatibility and DocMDP enforcement for: {input_path}")
    logger.info("IMPROVEMENTS: Using Helvetica font for universal compatibility + proper certification order")

    # 1. Load Certificate
    private_key, certificate, ca_certificates = load_certificate_data()
    signer_info = get_signer_info_from_cert(certificate)
    appearance_config = SignatureAppearance(signer_info)

    # 2. Prepare Temporary Files
    temp_dir = tempfile.mkdtemp()
    certified_pdf_path = os.path.join(temp_dir, "certified.pdf")
    logger.debug(f"Using temporary directory: {temp_dir}")

    try:
        # STEP 1: Apply Certification Signature FIRST (CRITICAL FIX)
        logger.info("STEP 1: Applying Certification Signature FIRST (MDP - No Changes Allowed)...")
        certify_dct = {
            "sigflags": 3, # Mark as signed
            "sigpage": 0, # Apply to first page (covers whole doc)
            "sigfield": "CertificationSig", # Unique field name
            "auto_sigfield": True,
            # CRITICAL: No signaturebox for invisible certification signature
            # When signaturebox is None or missing, endesive creates invisible signature
            # "reason" field removed as per requirements
            "location": signer_info.get('locality', 'Chennai'),
            "contact": signer_info.get('email', ''),
            "signingdate": datetime.now(dt_timezone.utc).strftime("D:%Y%m%d%H%M%S+00'00'"),
            # --- Enhanced Certification Specific Flags for Better DocMDP Enforcement ---
            "certification_level": 1, # 1 = No changes allowed (strictest level)
            "subfilter": "/adbe.pkcs7.detached",
            # Add explicit DocMDP reference for better enforcement
            "docmdp": 1,  # Explicit DocMDP level 1
        }
        if TSA_URL:
             certify_dct["tsaurl"] = TSA_URL

        with open(input_path, 'rb') as f_in:
            pdf_data_in = f_in.read()

        certify_signature_data = endesive_cms.sign(
            pdf_data_in,
            certify_dct,
            private_key,
            certificate,
            ca_certificates,
            "sha256" # Recommended hash algorithm
        )

        with open(certified_pdf_path, 'wb') as f_out:
            f_out.write(pdf_data_in)
            f_out.write(certify_signature_data)
        logger.info(f"Certification signature applied FIRST (INVISIBLE - no signaturebox), saved to: {certified_pdf_path}")
        logger.info("CRITICAL: Certification signature is invisible and should not appear as a visible signature on any page")

        # STEP 2: Apply Visible Approval Signatures to Each Page
        page_count = get_pdf_page_count(certified_pdf_path)
        logger.info(f"STEP 2: Applying visible approval signatures to {page_count} pages...")
        current_pdf_path = certified_pdf_path

        for page_num in range(page_count):
            logger.info(f"Signing page {page_num + 1} of {page_count}...")
            page_output_path = os.path.join(temp_dir, f"page_{page_num}_signed.pdf")

            with open(current_pdf_path, 'rb') as f_in:
                pdf_data_page_in = f_in.read()

            # Prepare signature dictionary for this page
            page_sig_dct = {
                "sigflags": 3, # AppendOnly / SignaturesExist
                "sigpage": page_num,
                "sigfield": f"ApprovalSignature_Page{page_num + 1}", # Unique field per page
                "auto_sigfield": True,
                "signaturebox": appearance_config.box,
                "subfilter": "/adbe.pkcs7.detached",
                # Add LTV info if TSA is configured
                **({ "tsaurl": TSA_URL } if TSA_URL else {}),
                # Add appearance details
                **appearance_config.build_appearance_dict(page_num)
            }

            # Apply the signature for the current page
            page_signature_data = endesive_cms.sign(
                pdf_data_page_in,
                page_sig_dct,
                private_key,
                certificate,
                ca_certificates,
                "sha256"
            )

            # Write the incrementally signed PDF for this page
            with open(page_output_path, 'wb') as f_out:
                f_out.write(pdf_data_page_in)
                f_out.write(page_signature_data)

            # Update the current PDF path for the next iteration
            current_pdf_path = page_output_path
            logger.info(f"Page {page_num + 1} signed, saved to: {page_output_path}")

        # 3. Move the final signed PDF to the output path
        shutil.move(current_pdf_path, output_path)
        logger.info(f"Multi-page signing with PROPER DocMDP enforcement complete. Final PDF saved to: {output_path}")
        logger.info("CRITICAL: Certification signature was applied FIRST to ensure proper document protection")

        return output_path

    except Exception as e:
        logger.error(f"Error during multi-page signing: {e}", exc_info=True)
        raise
    finally:
        # Clean up temporary directory
        try:
            shutil.rmtree(temp_dir)
            logger.debug(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as cleanup_error:
            logger.warning(f"Failed to clean up temporary directory {temp_dir}: {cleanup_error}")


def sign_pdf_multi_page(input_path, output_path, user=None):
    """
    Signs each page of a PDF document with a visible approval signature,
    after applying an initial certification signature to lock the document.

    Args:
        input_path (str): Path to the input PDF file.
        output_path (str): Path to save the final signed PDF file.
        user: Django user object (optional, for logging).

    Returns:
        str: Path to the signed PDF file.

    Raises:
        Exception: If endesive is not available or signing fails.
        FileNotFoundError: If the certificate file is not found.
        ValueError: If the certificate password is incorrect.
    """
    if not ENDESIVE_AVAILABLE:
        raise Exception("Endesive library is required for PDF signing.")

    logger.info(f"Starting multi-page signing process for: {input_path}")

    # 1. Load Certificate
    private_key, certificate, ca_certificates = load_certificate_data()
    signer_info = get_signer_info_from_cert(certificate)
    appearance_config = SignatureAppearance(signer_info)

    # 2. Prepare Temporary Files
    temp_dir = tempfile.mkdtemp()
    certified_pdf_path = os.path.join(temp_dir, "certified.pdf")
    logger.debug(f"Using temporary directory: {temp_dir}")

    try:
        # 3. Apply Certification Signature (MDP - No Changes Allowed)
        # CRITICAL: This must be applied FIRST to properly enforce document protection
        logger.info("Applying Certification Signature FIRST (MDP - No Changes Allowed)...")
        certify_dct = {
            "sigflags": 3, # Mark as signed
            "sigpage": 0, # Apply to first page (covers whole doc)
            "sigfield": "CertificationSig", # Unique field name
            "auto_sigfield": True,
            # CRITICAL: No signaturebox for invisible certification signature
            # When signaturebox is None or missing, endesive creates invisible signature
            # "reason" field removed as per requirements
            "location": signer_info.get('locality', 'Chennai'),
            "contact": signer_info.get('email', ''),
            "signingdate": datetime.now(dt_timezone.utc).strftime("D:%Y%m%d%H%M%S+00'00'"),
            # --- Enhanced Certification Specific Flags for Better DocMDP Enforcement ---
            "certification_level": 1, # 1 = No changes allowed (strictest level)
            "subfilter": "/adbe.pkcs7.detached",
            # Add explicit DocMDP reference for better enforcement
            "docmdp": 1,  # Explicit DocMDP level 1
        }
        if TSA_URL:
             certify_dct["tsaurl"] = TSA_URL

        with open(input_path, 'rb') as f_in:
            pdf_data_in = f_in.read()

        certify_signature_data = endesive_cms.sign(
            pdf_data_in,
            certify_dct,
            private_key,
            certificate,
            ca_certificates,
            "sha256" # Recommended hash algorithm
            # attrs=None # Removed: No signed attributes needed for certification usually
        )

        with open(certified_pdf_path, 'wb') as f_out:
            f_out.write(pdf_data_in)
            f_out.write(certify_signature_data)
        logger.info(f"Certification signature applied FIRST (INVISIBLE - no signaturebox), saved to: {certified_pdf_path}")
        logger.info("CRITICAL: Certification signature is invisible and should not appear as a visible signature on any page")

        # 4. Apply Visible Approval Signatures to Each Page
        page_count = get_pdf_page_count(certified_pdf_path)
        logger.info(f"Applying visible approval signatures to {page_count} pages...")
        current_pdf_path = certified_pdf_path

        for page_num in range(page_count):
            logger.info(f"Signing page {page_num + 1} of {page_count}...")
            page_output_path = os.path.join(temp_dir, f"page_{page_num}_signed.pdf")

            with open(current_pdf_path, 'rb') as f_in:
                pdf_data_page_in = f_in.read()

            # Prepare signature dictionary for this page
            page_sig_dct = {
                "sigflags": 3, # AppendOnly / SignaturesExist
                "sigpage": page_num,
                "sigfield": f"ApprovalSignature_Page{page_num + 1}", # Unique field per page
                "auto_sigfield": True,
                "signaturebox": appearance_config.box,
                "subfilter": "/adbe.pkcs7.detached",
                # Add LTV info if TSA is configured
                **({ "tsaurl": TSA_URL } if TSA_URL else {}),
                # Add appearance details
                **appearance_config.build_appearance_dict(page_num)
            }

            # Apply the signature for the current page
            page_signature_data = endesive_cms.sign(
                pdf_data_page_in,
                page_sig_dct,
                private_key,
                certificate,
                ca_certificates,
                "sha256"
            )

            # Write the incrementally signed PDF for this page
            with open(page_output_path, 'wb') as f_out:
                f_out.write(pdf_data_page_in)
                f_out.write(page_signature_data)

            # Update the current PDF path for the next iteration
            current_pdf_path = page_output_path
            logger.info(f"Page {page_num + 1} signed, saved to: {page_output_path}")

        # 5. Move the final signed PDF to the output path
        shutil.move(current_pdf_path, output_path)
        logger.info(f"Multi-page signing complete. Final PDF saved to: {output_path}")

        return output_path

    except Exception as e:
        logger.error(f"Error during multi-page signing process: {e}", exc_info=True)
        # Attempt to copy the original file if signing failed catastrophically
        if not os.path.exists(output_path) and os.path.exists(input_path):
             try:
                 shutil.copy2(input_path, output_path)
                 logger.warning("Signing failed, copied original file to output path.")
             except Exception as copy_err:
                 logger.error(f"Failed to copy original file after signing error: {copy_err}")
        raise # Re-raise the original exception

    finally:
        # 6. Clean up temporary directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            logger.debug(f"Cleaned up temporary directory: {temp_dir}")

# --- Verification Logic (Optional but Recommended) --- #

def verify_pdf_signature(pdf_path):
    """
    Verify all digital signatures within a PDF file using endesive.

    Args:
        pdf_path (str): Path to the PDF file to verify.

    Returns:
        list: A list of verification results for each signature found.
              Each result is a tuple: (signature_name, valid_bool, details_dict).
    """
    if not ENDESIVE_AVAILABLE or endesive_verify_func is None:
        logger.warning("Endesive not available, cannot verify PDF signatures.")
        return []

    results = []
    try:
        with open(pdf_path, 'rb') as pdf_file:
            pdf_data = pdf_file.read()

        # Endesive verify returns list of (signature_name, cert_bytes, signed_data, valid_bool)
        # We need to adapt this or use a more detailed verification if available
        # The basic verify function might only check cryptographic integrity.
        # For full validation (trust chain, revocation), more complex logic or
        # integration with certvalidator might be needed.

        # Placeholder: Using the basic verify function
        # Note: This basic verify might not check trust chain or revocation status effectively.
        verified_signatures = endesive_verify_func(pdf_data, []) # Pass empty trusted certs list for now

        if not verified_signatures:
            logger.info(f"No signatures found or verification failed in {pdf_path}")
            return []

        logger.info(f"Found {len(verified_signatures)} signatures in {pdf_path}")
        logger.debug(f"Raw verification results: {verified_signatures}") # DEBUG: Print raw results

        for i, verification_result in enumerate(verified_signatures):
            try:
                # Based on endesive examples, verify returns 5 elements per signature
                # (signature_name, cert_bytes, signed_data, signature_ok, hash_ok)
                if len(verification_result) == 5:
                    sig_name, cert_bytes, signed_data, signature_ok, hash_ok = verification_result
                    sig_name_str = sig_name.decode("utf-8", errors="ignore")
                    details = {
                        "signature_name": sig_name_str,
                        "cryptographically_valid": signature_ok, # Signature integrity check
                        "hash_ok": hash_ok, # Document hash check
                        "certificate_size": len(cert_bytes) if cert_bytes else 0,
                        # TODO: Add certificate chain validation details if needed using certvalidator
                    }
                    logger.info(f"  Signature {i+1} ('{sig_name_str}'): Signature OK = {signature_ok}, Hash OK = {hash_ok}")
                    # Append tuple: (name, validity_status, details_dict)
                    results.append((sig_name_str, signature_ok and hash_ok, details))
                else:
                    logger.warning(f"Unexpected number of values in verification result tuple for signature {i+1}: {len(verification_result)}. Raw data: {verification_result}. Skipping.")
            except Exception as e:
                logger.error(f"Error processing verification result {i+1}: {e}")
                continue

    except Exception as e:
        logger.error(f"Error verifying signatures in {pdf_path}: {e}", exc_info=True)

    return results

# --- Compatibility Functions for Django Views --- #

def ensure_directories_exist():
    """Ensure required directories exist."""
    os.makedirs(CERTIFICATE_DIR, exist_ok=True)
    if DJANGO_AVAILABLE:
        try:
            from django.conf import settings
            os.makedirs(os.path.join(settings.MEDIA_ROOT, 'signed'), exist_ok=True)
            os.makedirs(os.path.join(settings.MEDIA_ROOT, 'temp'), exist_ok=True)
            os.makedirs(os.path.join(settings.MEDIA_ROOT, 'uploads'), exist_ok=True)
        except:
            pass

def sign_pdf_cryptographically(input_path, output_path, user=None, use_pyhanko=False):
    """
    Compatibility wrapper for PDF signing with improved DocMDP enforcement.

    Args:
        input_path (str): Path to input PDF
        output_path (str): Path to output PDF
        user: Django user object (optional)
        use_pyhanko (bool): Whether to use PyHanko (recommended for better DocMDP enforcement)

    Returns:
        str: Path to signed PDF
    """
    if use_pyhanko:
        try:
            from .pyhanko_signer import sign_pdf_multi_page_pyhanko
            logger.info("Using PyHanko implementation with proper DocMDP enforcement")
            return sign_pdf_multi_page_pyhanko(input_path, output_path, user)
        except ImportError:
            logger.warning("PyHanko not available, falling back to improved endesive implementation")
            return sign_pdf_multi_page_with_proper_mdp(input_path, output_path, user)
    else:
        logger.info("Using improved endesive implementation with proper DocMDP enforcement")
        return sign_pdf_multi_page_with_proper_mdp(input_path, output_path, user)

def get_certificate_info():
    """Get certificate information."""
    try:
        private_key, certificate, ca_certificates = load_certificate_data()
        signer_info = get_signer_info_from_cert(certificate)

        info = f"Certificate Information:\n"
        info += f"Common Name: {signer_info['common_name']}\n"
        info += f"Organization: {signer_info['organization']}\n"
        info += f"Country: {signer_info['country']}\n"
        info += f"State: {signer_info['state']}\n"
        info += f"Email: {signer_info['email']}\n"
        info += f"Valid From: {certificate.not_valid_before_utc}\n"
        info += f"Valid Until: {certificate.not_valid_after_utc}\n"
        info += f"Serial Number: {certificate.serial_number}\n"
        return info
    except Exception as e:
        return f"Certificate information not available: {e}"

def create_pdfa_compliant_signature(input_path, output_path, user=None):
    """
    Compatibility wrapper for improved PDF signing with proper DocMDP enforcement.
    Works for both single-page and multi-page PDFs.
    """
    logger.info("Using improved implementation with proper DocMDP enforcement for PDF/A compliant signature")
    return sign_pdf_multi_page_with_proper_mdp(input_path, output_path, user)

def _sign_with_endesive(input_path, output_path, user=None):
    """
    Compatibility wrapper for improved PDF signing with proper DocMDP enforcement.
    Works for both single-page and multi-page PDFs.
    """
    logger.info("Using improved endesive implementation with proper DocMDP enforcement")
    return sign_pdf_multi_page_with_proper_mdp(input_path, output_path, user)

def sign_each_page_with_endesive(input_path, output_path, user=None):
    """
    Compatibility wrapper for improved PDF signing with proper DocMDP enforcement.
    Works for both single-page and multi-page PDFs.
    """
    logger.info("Using improved implementation for each page signing with proper DocMDP enforcement")
    return sign_pdf_multi_page_with_proper_mdp(input_path, output_path, user)

def sign_each_page_individually_with_endesive(input_path, output_path, user=None):
    """
    Compatibility wrapper for improved PDF signing with proper DocMDP enforcement.
    Works for both single-page and multi-page PDFs.
    """
    logger.info("Using improved implementation for individual page signing with proper DocMDP enforcement")
    return sign_pdf_multi_page_with_proper_mdp(input_path, output_path, user)

def sign_pdf_single_page(input_path, output_path, user=None):
    """
    Signs a single-page PDF document with proper DocMDP enforcement.

    This function is specifically for single-page PDFs but uses the same improved
    multi-page implementation to ensure consistent document protection enforcement.

    CRITICAL: Uses the same approach as multi-page signing:
    1. Applies certification signature FIRST with DocMDP level 1 (NO CHANGES ALLOWED)
    2. Applies visible approval signature to the single page
    3. Ensures "Changes NOT allowed" is displayed in PDF viewers

    Args:
        input_path (str): Path to the input single-page PDF file.
        output_path (str): Path to save the final signed PDF file.
        user: Django user object (optional, for logging).

    Returns:
        str: Path to the signed PDF file.

    Raises:
        Exception: If endesive is not available or signing fails.
        FileNotFoundError: If the certificate file is not found.
        ValueError: If the certificate password is incorrect.
    """
    logger.info(f"Signing single-page PDF with proper DocMDP enforcement: {input_path}")
    logger.info("Using improved multi-page implementation for consistent document protection")
    return sign_pdf_multi_page_with_proper_mdp(input_path, output_path, user)

def verify_individual_page_signatures(pdf_path):
    """Compatibility wrapper for verify_pdf_signature."""
    return verify_pdf_signature(pdf_path)

def resolve_custom_save_path(custom_path, filename, user=None):
    """
    Resolve custom save path with proper handling of absolute and relative paths.
    This function mirrors the logic used in batch processing for consistency.
    """
    if not custom_path:
        return filename

    # Determine the final directory path
    if os.path.isabs(custom_path):
        # Already a full path
        custom_dir = custom_path
        logger.info(f"Using absolute custom save path: {custom_dir}")
    else:
        # Relative path - create in user's Documents or current directory
        if os.name == 'nt':  # Windows
            documents_dir = os.path.join(os.path.expanduser('~'), 'Documents')
        else:  # Linux/Mac
            documents_dir = os.path.expanduser('~')
        custom_dir = os.path.join(documents_dir, custom_path)
        logger.info(f"Using relative custom save path: {custom_dir} (base: {documents_dir})")

    # Ensure the directory exists
    try:
        os.makedirs(custom_dir, exist_ok=True)
        logger.info(f"Created/verified custom save directory: {custom_dir}")
    except Exception as e:
        logger.error(f"Failed to create custom save directory {custom_dir}: {e}")
        raise Exception(f"Cannot create save directory: {custom_dir}")

    # Validate the directory is writable
    if not os.access(custom_dir, os.W_OK):
        logger.error(f"Custom save directory is not writable: {custom_dir}")
        raise Exception(f"Save directory is not writable: {custom_dir}")

    final_path = os.path.join(custom_dir, filename)
    logger.info(f"Resolved custom save path: {final_path}")
    return final_path

def process_batch_signing(files, user, save_location=None, naming_convention='signed_{original_name}',
                         custom_naming_pattern='', apply_to_all_pages=True):
    """Improved batch processing with proper Django file handling."""
    import tempfile
    import shutil
    from datetime import datetime

    if DJANGO_AVAILABLE:
        from django.conf import settings
        from django.core.files.storage import default_storage

    results = {
        'total_files': len(files),
        'successful_files': 0,
        'failed_files': 0,
        'processed_files': [],
        'errors': [],
        'batch_job_id': f"batch_{user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    }

    # Create temporary directory for processing
    temp_dir = tempfile.mkdtemp(prefix='pdf_batch_')

    try:
        for pdf_file in files:
            try:
                logger.info(f"Processing batch file: {pdf_file.name}")

                # Create safe filename
                safe_filename = f"{user.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{pdf_file.name}"

                # Save uploaded file temporarily using Django storage
                temp_input_path = os.path.join(temp_dir, f"input_{safe_filename}")

                # Write file chunks to temporary location
                with open(temp_input_path, 'wb') as temp_file:
                    for chunk in pdf_file.chunks():
                        temp_file.write(chunk)

                # Determine output path
                if save_location:
                    # Custom save location - resolve to full path
                    if os.path.isabs(save_location):
                        # Already a full path
                        custom_dir = save_location
                    else:
                        # Relative path - create in user's Documents or current directory
                        if os.name == 'nt':  # Windows
                            documents_dir = os.path.join(os.path.expanduser('~'), 'Documents')
                        else:  # Linux/Mac
                            documents_dir = os.path.expanduser('~')
                        custom_dir = os.path.join(documents_dir, save_location)

                    # Ensure directory exists
                    os.makedirs(custom_dir, exist_ok=True)
                    logger.info(f"Using custom save directory: {custom_dir}")

                    if naming_convention == 'custom' and custom_naming_pattern:
                        # Apply custom naming pattern
                        output_filename = custom_naming_pattern.format(
                            original_name=os.path.splitext(pdf_file.name)[0],
                            user=user.username,
                            timestamp=datetime.now().strftime('%Y%m%d_%H%M%S'),
                            date=datetime.now().strftime('%Y%m%d')
                        ) + '.pdf'
                    else:
                        # Default naming convention
                        output_filename = f"signed_{pdf_file.name}"

                    final_output_path = os.path.join(custom_dir, output_filename)
                    logger.info(f"Final output path: {final_output_path}")
                else:
                    # Use Django media storage
                    if DJANGO_AVAILABLE:
                        output_filename = f"signed_{safe_filename}"
                        final_output_path = os.path.join(settings.MEDIA_ROOT, 'signed', output_filename)
                        os.makedirs(os.path.dirname(final_output_path), exist_ok=True)
                    else:
                        final_output_path = os.path.join(temp_dir, f"signed_{safe_filename}")

                # Sign the PDF
                logger.info(f"Signing PDF: {temp_input_path} -> {final_output_path}")
                signed_path = sign_pdf_multi_page(temp_input_path, final_output_path, user)

                # Verify the file was actually created
                if os.path.exists(signed_path):
                    file_size = os.path.getsize(signed_path)
                    logger.info(f"File successfully created: {signed_path} ({file_size} bytes)")
                else:
                    raise Exception(f"Signed file was not created at expected location: {signed_path}")

                results['successful_files'] += 1
                # Determine save location for response
                actual_save_location = None
                if save_location:
                    if os.path.isabs(save_location):
                        actual_save_location = save_location
                    else:
                        if os.name == 'nt':  # Windows
                            documents_dir = os.path.join(os.path.expanduser('~'), 'Documents')
                        else:  # Linux/Mac
                            documents_dir = os.path.expanduser('~')
                        actual_save_location = os.path.join(documents_dir, save_location)

                results['processed_files'].append({
                    'filename': pdf_file.name,
                    'status': 'success',
                    'output_path': signed_path,
                    'save_location': actual_save_location,
                    'file_size': file_size,
                    'download_url': f'/pdf-signature/download/{os.path.basename(signed_path)}/' if not save_location else None
                })

                logger.info(f"Successfully processed: {pdf_file.name} -> {signed_path}")

            except Exception as e:
                logger.error(f"Error processing {pdf_file.name}: {e}")
                results['failed_files'] += 1
                results['errors'].append(f"{pdf_file.name}: {str(e)}")
                results['processed_files'].append({
                    'filename': pdf_file.name,
                    'status': 'failed',
                    'error': str(e)
                })

    finally:
        # Clean up temporary directory
        try:
            shutil.rmtree(temp_dir)
            logger.debug(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to clean up temporary directory {temp_dir}: {e}")

    logger.info(f"Batch processing completed: {results['successful_files']}/{results['total_files']} successful")
    return results

def get_batch_job_status(job_id, user):
    """Get batch job status."""
    return {
        'job_id': job_id,
        'status': 'completed',
        'progress': 100,
        'message': 'Batch processing completed'
    }

# --- Deprecated/Removed Functions --- #

# Removed create_self_signed_certificate - Unsafe for trusted signing
# Removed load_emudhra_certificate - .cer files cannot be used for signing
# Removed ensure_certificate_exists - Replaced by load_certificate_data which requires a valid P12
# Removed get_certificate_path, get_certificate_info_path - Paths are now configured
# Removed create_personal_certificate_files, load_personal_certificate_files, get_personal_certificate_path - Standardized on single P12 config
# Removed sign_pdf_cryptographically, create_pdfa_compliant_signature - Replaced by sign_pdf_multi_page
# Removed _sign_with_endesive - Logic integrated into sign_pdf_multi_page
# Removed build_signature_appearance, build_signature_appearance_dict - Integrated into SignatureAppearance class
# Removed create_signature_config_for_user - Simplified appearance logic
# Removed SignatureConfig class - Replaced by simpler SignatureAppearance

# --- Example Usage (if run directly) --- #

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    logger.info("Running PDF Signature Utility Example")

    # --- Configuration --- #
    # Ensure you have a PKCS#12 certificate file (.p12) and set the path and password
    # For testing, you might need to generate one using OpenSSL or similar tools
    # Example generation (replace with your details):
    # openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes -subj "/C=IN/ST=Tamil Nadu/L=Chennai/O=MyOrg/OU=Test/CN=Test Signer/emailAddress=test@example.com"
    # openssl pkcs12 -export -out signing_cert.p12 -inkey key.pem -in cert.pem -name "Test Signing Certificate"
    # (You will be prompted for an export password - set this in CERTIFICATE_PASSWORD)

    # Create a dummy certificate directory if it doesn't exist for the example
    if not os.path.exists(CERTIFICATE_DIR):
        os.makedirs(CERTIFICATE_DIR)
        logger.warning(f"Created certificate directory: {CERTIFICATE_DIR}")
        logger.warning(f"Please place your signing_cert.p12 file in this directory and configure the password.")

    # Create dummy input PDF for testing
    input_pdf = "/home/ubuntu/upload/sample.pdf" # Use user-provided sample PDF
    output_pdf = "/home/ubuntu/sample_multipage_signed.pdf"

    # Create a dummy multi-page PDF if it doesn't exist
    if not os.path.exists(input_pdf):
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter
            c = canvas.Canvas(input_pdf, pagesize=letter)
            for i in range(3): # Create 3 pages
                c.drawString(100, 750, f"This is page {i + 1} of the sample document.")
                c.showPage()
            c.save()
            logger.info(f"Created dummy multi-page PDF: {input_pdf}")
        except ImportError:
            logger.error("ReportLab not found. Cannot create dummy PDF. Please provide a multi-page PDF at {input_pdf}")
            exit(1)
        except Exception as e:
             logger.error(f"Failed to create dummy PDF: {e}")
             exit(1)

    # --- Signing --- #
    try:
        logger.info(f"Signing PDF: {input_pdf} -> {output_pdf}")
        signed_file = sign_pdf_multi_page(input_pdf, output_pdf)
        logger.info(f"Successfully signed PDF: {signed_file}")

        # --- Verification --- #
        logger.info(f"Verifying signatures in: {signed_file}")
        verification_results = verify_pdf_signature(signed_file)
        if verification_results:
            logger.info("Verification Results:")
            for name, is_valid, details in verification_results:
                logger.info(f"  - Signature: {name}, Valid: {is_valid}")
        else:
            logger.warning("No signatures verified.")

    except FileNotFoundError as e:
        logger.error(f"Signing failed: Certificate file not found. {e}")
    except ValueError as e:
        logger.error(f"Signing failed: {e}") # Likely incorrect password
    except Exception as e:
        logger.error(f"Signing failed: {e}", exc_info=True)

