from django.urls import path
from . import views

app_name = 'pdf_signature'

urlpatterns = [
    # Main PDF signing flow
    path('', views.PDFSignatureView.as_view(), name='home'),
    path('download/', views.PDFDownloadView.as_view(), name='download'),
    path('verify/', views.PDFVerifyView.as_view(), name='verify'),
    
    # Legacy URLs (kept for backward compatibility)
    path('upload/', views.PDFUploadView.as_view(), name='upload'),
    path('download/<str:filename>/', views.PDFDownloadView.as_view(), name='legacy_download'),
    path('verify/upload/', views.PDFVerifyUploadView.as_view(), name='verify_upload'),

    # Batch processing URLs
    path('batch/', views.BatchPDFSigningView.as_view(), name='batch_sign'),
    path('batch/upload/', views.BatchPDFUploadView.as_view(), name='batch_upload'),
    path('batch/status/<uuid:job_id>/', views.BatchJobStatusView.as_view(), name='batch_status'),
    path('batch/jobs/', views.BatchJobListView.as_view(), name='batch_jobs'),
    path('folder/select/', views.FolderSelectionView.as_view(), name='folder_select'),

    # USB Key signing URLs
    path('usb-key/detect/', views.USBKeyDetectionView.as_view(), name='usb_key_detect'),
]
