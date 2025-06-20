from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class BatchSigningJob(models.Model):
    """
    Model to track batch PDF signing operations.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('partial', 'Partially Completed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='batch_signing_jobs')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_files = models.PositiveIntegerField(default=0)
    processed_files = models.PositiveIntegerField(default=0)
    successful_files = models.PositiveIntegerField(default=0)
    failed_files = models.PositiveIntegerField(default=0)
    save_location = models.CharField(max_length=500, blank=True, null=True)
    naming_convention = models.CharField(max_length=100, default='signed_{original_name}')
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Batch Signing Job'
        verbose_name_plural = 'Batch Signing Jobs'

    def __str__(self):
        return f"Batch Job {self.id} - {self.user.username} ({self.status})"

    @property
    def progress_percentage(self):
        """Calculate progress percentage."""
        if self.total_files == 0:
            return 0
        return (self.processed_files / self.total_files) * 100

    @property
    def is_completed(self):
        """Check if job is completed."""
        return self.status in ['completed', 'failed', 'partial']


class PDFSigningTask(models.Model):
    """
    Model to track individual PDF files within a batch signing job.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch_job = models.ForeignKey(BatchSigningJob, on_delete=models.CASCADE, related_name='tasks')
    original_filename = models.CharField(max_length=255)
    original_file_path = models.CharField(max_length=500)
    signed_filename = models.CharField(max_length=255, blank=True, null=True)
    signed_file_path = models.CharField(max_length=500, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    file_size = models.PositiveIntegerField(default=0)
    pages_count = models.PositiveIntegerField(default=0)
    processing_started_at = models.DateTimeField(blank=True, null=True)
    processing_completed_at = models.DateTimeField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['original_filename']
        verbose_name = 'PDF Signing Task'
        verbose_name_plural = 'PDF Signing Tasks'

    def __str__(self):
        return f"{self.original_filename} - {self.status}"

    @property
    def processing_duration(self):
        """Calculate processing duration."""
        if self.processing_started_at and self.processing_completed_at:
            return self.processing_completed_at - self.processing_started_at
        return None
