#!/usr/bin/env python3
"""
Certificate Authority (CA) Infrastructure for PDF Signing
Creates proper CA-signed certificates with revocation checking support
"""

import os
import logging
from datetime import datetime, timedelta, timezone as dt_timezone
from cryptography import x509
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

class PDFSigningCA:
    """
    Certificate Authority for PDF signing certificates.
    Creates proper CA infrastructure with revocation support.
    """
    
    def __init__(self, ca_dir="certificates/ca"):
        self.ca_dir = ca_dir
        self.ca_cert_path = os.path.join(ca_dir, "ca_cert.pem")
        self.ca_key_path = os.path.join(ca_dir, "ca_key.pem")
        self.crl_path = os.path.join(ca_dir, "ca_crl.pem")
        self.serial_file = os.path.join(ca_dir, "serial.txt")
        
        # Ensure CA directory exists
        os.makedirs(ca_dir, exist_ok=True)
        
    def create_ca_certificate(self):
        """Create the root CA certificate and private key."""
        logger.info("Creating Certificate Authority (CA) certificate...")
        
        # Generate CA private key
        ca_private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,  # Stronger key for CA
            backend=default_backend()
        )
        
        # Create CA certificate subject
        ca_subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Tamil Nadu"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Chennai"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "FTE Digital Workspace CA"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Certificate Authority"),
            x509.NameAttribute(NameOID.COMMON_NAME, "FTE PDF Signing Root CA"),
            x509.NameAttribute(NameOID.EMAIL_ADDRESS, "ca@fte.com"),
        ])
        
        # Create CA certificate
        ca_cert = x509.CertificateBuilder().subject_name(
            ca_subject
        ).issuer_name(
            ca_subject  # Self-signed CA
        ).public_key(
            ca_private_key.public_key()
        ).serial_number(
            1  # CA gets serial number 1
        ).not_valid_before(
            datetime.now(dt_timezone.utc)
        ).not_valid_after(
            datetime.now(dt_timezone.utc) + timedelta(days=365 * 10)  # 10 years
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=0),  # This is a CA
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,  # Can sign certificates
                crl_sign=True,      # Can sign CRLs
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).add_extension(
            x509.SubjectKeyIdentifier.from_public_key(ca_private_key.public_key()),
            critical=False,
        ).add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_private_key.public_key()),
            critical=False,
        ).sign(ca_private_key, hashes.SHA256(), backend=default_backend())
        
        # Save CA certificate
        with open(self.ca_cert_path, "wb") as f:
            f.write(ca_cert.public_bytes(serialization.Encoding.PEM))
            
        # Save CA private key (encrypted)
        with open(self.ca_key_path, "wb") as f:
            f.write(ca_private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.BestAvailableEncryption(b"ca_password_2024")
            ))
            
        # Initialize serial number file
        with open(self.serial_file, "w") as f:
            f.write("2")  # Next serial number (CA used 1)
            
        logger.info(f"CA certificate created: {self.ca_cert_path}")
        return ca_cert, ca_private_key
        
    def load_ca_certificate(self):
        """Load existing CA certificate and private key."""
        if not os.path.exists(self.ca_cert_path) or not os.path.exists(self.ca_key_path):
            return self.create_ca_certificate()
            
        # Load CA certificate
        with open(self.ca_cert_path, "rb") as f:
            ca_cert = x509.load_pem_x509_certificate(f.read(), backend=default_backend())
            
        # Load CA private key
        with open(self.ca_key_path, "rb") as f:
            ca_private_key = serialization.load_pem_private_key(
                f.read(),
                password=b"ca_password_2024",
                backend=default_backend()
            )
            
        return ca_cert, ca_private_key
        
    def get_next_serial_number(self):
        """Get the next serial number for certificate issuance."""
        if not os.path.exists(self.serial_file):
            serial = 2
        else:
            with open(self.serial_file, "r") as f:
                serial = int(f.read().strip())
                
        # Update serial file
        with open(self.serial_file, "w") as f:
            f.write(str(serial + 1))
            
        return serial
        
    def create_pdf_signing_certificate(self, common_name="ARUL M", email="m.arul@fte.com"):
        """Create a CA-signed PDF signing certificate."""
        logger.info(f"Creating PDF signing certificate for: {common_name}")
        
        # Load CA
        ca_cert, ca_private_key = self.load_ca_certificate()
        
        # Generate certificate private key
        cert_private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Create certificate subject
        cert_subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "IN"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Tamil Nadu"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Chennai"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "PERSONAL"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Individual"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
            x509.NameAttribute(NameOID.EMAIL_ADDRESS, email),
        ])
        
        # Get serial number
        serial_number = self.get_next_serial_number()
        
        # Create certificate
        cert = x509.CertificateBuilder().subject_name(
            cert_subject
        ).issuer_name(
            ca_cert.subject  # Issued by CA
        ).public_key(
            cert_private_key.public_key()
        ).serial_number(
            serial_number
        ).not_valid_before(
            datetime.now(dt_timezone.utc)
        ).not_valid_after(
            datetime.now(dt_timezone.utc) + timedelta(days=365 * 3)  # 3 years
        ).add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=True,  # Non-repudiation
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        ).add_extension(
            x509.ExtendedKeyUsage([
                ExtendedKeyUsageOID.CODE_SIGNING,
                ExtendedKeyUsageOID.EMAIL_PROTECTION,
                ExtendedKeyUsageOID.CLIENT_AUTH,
            ]),
            critical=True,
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.RFC822Name(email),
            ]),
            critical=False,
        ).add_extension(
            x509.SubjectKeyIdentifier.from_public_key(cert_private_key.public_key()),
            critical=False,
        ).add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_private_key.public_key()),
            critical=False,
        ).add_extension(
            # Add CRL Distribution Points for revocation checking (using HTTP URI for compatibility)
            x509.CRLDistributionPoints([
                x509.DistributionPoint(
                    full_name=[x509.UniformResourceIdentifier("http://localhost:8000/pdf-signature/crl/")],
                    relative_name=None,
                    reasons=None,
                    crl_issuer=None,
                )
            ]),
            critical=False,
        ).add_extension(
            # Add Authority Information Access for OCSP (optional)
            x509.AuthorityInformationAccess([
                x509.AccessDescription(
                    access_method=x509.oid.AuthorityInformationAccessOID.CA_ISSUERS,
                    access_location=x509.UniformResourceIdentifier("http://localhost:8000/pdf-signature/ca-cert/")
                ),
            ]),
            critical=False,
        ).sign(ca_private_key, hashes.SHA256(), backend=default_backend())
        
        # Create PKCS#12 bundle using OpenSSL (fallback for older cryptography versions)
        try:
            # Try new cryptography API first
            from cryptography.hazmat.primitives import serialization
            if hasattr(serialization, 'pkcs12'):
                p12_data = serialization.pkcs12.serialize_key_and_certificates(
                    name=f"{common_name} PDF Signing Certificate".encode('utf-8'),
                    key=cert_private_key,
                    cert=cert,
                    cas=[ca_cert],  # Include CA certificate in bundle
                    encryption_algorithm=serialization.BestAvailableEncryption(b"digital_workspace_2024")
                )
            else:
                raise AttributeError("pkcs12 not available")
        except (AttributeError, ImportError):
            # Fallback: Create separate PEM files and use OpenSSL to create PKCS#12
            logger.warning("Using OpenSSL fallback for PKCS#12 creation")
            p12_data = self._create_pkcs12_with_openssl(cert_private_key, cert, ca_cert, common_name)
        
        # Save certificate files
        cert_dir = os.path.dirname(self.ca_dir)
        cert_path = os.path.join(cert_dir, "signing_cert.p12")
        ca_bundle_path = os.path.join(cert_dir, "ca_bundle.pem")
        
        # Save PKCS#12 file
        with open(cert_path, "wb") as f:
            f.write(p12_data)
            
        # Save CA bundle for verification
        with open(ca_bundle_path, "wb") as f:
            f.write(ca_cert.public_bytes(serialization.Encoding.PEM))
            
        logger.info(f"PDF signing certificate created: {cert_path}")
        logger.info(f"CA bundle created: {ca_bundle_path}")
        
        return cert_path, ca_bundle_path
        
    def create_crl(self, revoked_serials=None):
        """Create Certificate Revocation List (CRL)."""
        logger.info("Creating Certificate Revocation List (CRL)...")
        
        # Load CA
        ca_cert, ca_private_key = self.load_ca_certificate()
        
        if revoked_serials is None:
            revoked_serials = []
            
        # Create CRL builder
        crl_builder = x509.CertificateRevocationListBuilder()
        crl_builder = crl_builder.issuer_name(ca_cert.subject)
        crl_builder = crl_builder.last_update(datetime.now(dt_timezone.utc))
        crl_builder = crl_builder.next_update(datetime.now(dt_timezone.utc) + timedelta(days=30))
        
        # Add revoked certificates
        for serial in revoked_serials:
            revoked_cert = x509.RevokedCertificateBuilder().serial_number(
                serial
            ).revocation_date(
                datetime.now(dt_timezone.utc)
            ).build(backend=default_backend())
            crl_builder = crl_builder.add_revoked_certificate(revoked_cert)
            
        # Sign CRL
        crl = crl_builder.sign(ca_private_key, hashes.SHA256(), backend=default_backend())
        
        # Save CRL
        with open(self.crl_path, "wb") as f:
            f.write(crl.public_bytes(serialization.Encoding.PEM))
            
        logger.info(f"CRL created: {self.crl_path}")
        return self.crl_path

    def _create_pkcs12_with_openssl(self, private_key, certificate, ca_cert, common_name):
        """Create PKCS#12 bundle using OpenSSL command line (fallback)."""
        import tempfile
        import subprocess

        with tempfile.TemporaryDirectory() as temp_dir:
            # Save private key
            key_path = os.path.join(temp_dir, "key.pem")
            with open(key_path, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))

            # Save certificate
            cert_path = os.path.join(temp_dir, "cert.pem")
            with open(cert_path, "wb") as f:
                f.write(certificate.public_bytes(serialization.Encoding.PEM))

            # Save CA certificate
            ca_path = os.path.join(temp_dir, "ca.pem")
            with open(ca_path, "wb") as f:
                f.write(ca_cert.public_bytes(serialization.Encoding.PEM))

            # Create PKCS#12 using OpenSSL
            p12_path = os.path.join(temp_dir, "cert.p12")
            cmd = [
                "openssl", "pkcs12", "-export",
                "-out", p12_path,
                "-inkey", key_path,
                "-in", cert_path,
                "-certfile", ca_path,
                "-name", f"{common_name} PDF Signing Certificate",
                "-passout", "pass:digital_workspace_2024"
            ]

            try:
                subprocess.run(cmd, check=True, capture_output=True)
                with open(p12_path, "rb") as f:
                    return f.read()
            except subprocess.CalledProcessError as e:
                logger.error(f"OpenSSL PKCS#12 creation failed: {e}")
                # Create a simple PKCS#12 manually (basic version)
                return self._create_simple_pkcs12(private_key, certificate)

    def _create_simple_pkcs12(self, private_key, certificate):
        """Create a simple PKCS#12 bundle manually."""
        try:
            # Use pyOpenSSL if available
            from OpenSSL import crypto

            # Create PKCS#12 object
            p12 = crypto.PKCS12()
            p12.set_privatekey(crypto.PKey.from_cryptography_key(private_key))
            p12.set_certificate(crypto.X509.from_cryptography(certificate))

            # Export to PKCS#12 format
            return p12.export(passphrase=b"digital_workspace_2024")

        except ImportError:
            logger.error("Neither cryptography.pkcs12 nor pyOpenSSL available")
            logger.error("Please install pyOpenSSL: pip install pyOpenSSL")
            raise Exception("Cannot create PKCS#12 bundle - missing dependencies")


def setup_ca_infrastructure():
    """Set up complete CA infrastructure for PDF signing."""
    logger.info("Setting up Certificate Authority infrastructure...")
    
    ca = PDFSigningCA()
    
    # Create CA certificate
    ca.load_ca_certificate()
    
    # Create PDF signing certificate
    cert_path, ca_bundle_path = ca.create_pdf_signing_certificate()
    
    # Create initial CRL (empty)
    crl_path = ca.create_crl()
    
    logger.info("CA infrastructure setup complete!")
    logger.info(f"Certificate: {cert_path}")
    logger.info(f"CA Bundle: {ca_bundle_path}")
    logger.info(f"CRL: {crl_path}")
    
    return {
        'certificate_path': cert_path,
        'ca_bundle_path': ca_bundle_path,
        'crl_path': crl_path,
        'ca_cert_path': ca.ca_cert_path
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    setup_ca_infrastructure()
