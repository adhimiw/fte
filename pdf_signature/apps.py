import os
import logging
from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class PdfSignatureConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pdf_signature'
    
    def ready(self):
        """Run when the app is ready."""
        # Only run in the main process, not during management commands that don't load the server
        if os.environ.get('RUN_MAIN') or not os.environ.get('WERKZEUG_RUN_MAIN'):
            try:
                # Import here to avoid AppRegistryNotReady errors
                from .utils import ensure_directories_exist

                # Ensure the media root exists
                os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

                # Ensure all required directories exist
                ensure_directories_exist()

                # Log the configuration
                logger.info(f"PDF Signature App Ready. Media Root: {settings.MEDIA_ROOT}")

            except Exception as e:
                logger.error(f"Error initializing PDF Signature app: {str(e)}")
