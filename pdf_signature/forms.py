from django import forms
from django.core.exceptions import ValidationError
import os


class MultipleFileInput(forms.ClearableFileInput):
    """Custom widget for multiple file uploads."""
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """Custom field for multiple file uploads."""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class BatchPDFUploadForm(forms.Form):
    """
    Form for batch PDF upload and signing configuration.
    """
    NAMING_CONVENTION_CHOICES = [
        ('signed_{original_name}', 'signed_[original_name]'),
        ('{original_name}_signed', '[original_name]_signed'),
        ('signed_{timestamp}_{original_name}', 'signed_[timestamp]_[original_name]'),
        ('{user}_{timestamp}_{original_name}', '[user]_[timestamp]_[original_name]'),
        ('custom', 'Custom naming pattern'),
    ]
    
    pdf_files = MultipleFileField(
        widget=MultipleFileInput(attrs={
            'multiple': True,
            'accept': '.pdf',
            'class': 'form-control',
            'id': 'pdf-files'
        }),
        help_text='Select one or more PDF files to sign (max 10MB each)',
        required=True
    )
    
    save_location = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Leave empty to use default location',
            'readonly': True,
            'id': 'save-location'
        }),
        help_text='Click "Browse" to select a custom save location'
    )
    
    naming_convention = forms.ChoiceField(
        choices=NAMING_CONVENTION_CHOICES,
        initial='signed_{original_name}',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'naming-convention'
        }),
        help_text='Choose how to name the signed PDF files'
    )
    
    custom_naming_pattern = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., signed_{original_name}_{date}',
            'id': 'custom-naming-pattern',
            'style': 'display: none;'
        }),
        help_text='Available variables: {original_name}, {user}, {timestamp}, {date}'
    )
    
    apply_to_all_pages = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'apply-to-all-pages'
        }),
        help_text='Apply digital signature to cover all pages of each PDF'
    )
    
    def clean_pdf_files(self):
        """Validate uploaded PDF files."""
        files = self.files.getlist('pdf_files')
        
        if not files:
            raise ValidationError('Please select at least one PDF file.')
        
        if len(files) > 20:  # Limit batch size
            raise ValidationError('Maximum 20 files allowed per batch.')
        
        for file in files:
            # Check file extension
            if not file.name.lower().endswith('.pdf'):
                raise ValidationError(f'File "{file.name}" is not a PDF file.')
            
            # Check file size (10MB limit per file)
            if file.size > 10 * 1024 * 1024:
                raise ValidationError(f'File "{file.name}" exceeds 10MB size limit.')
        
        return files
    
    def clean_custom_naming_pattern(self):
        """Validate custom naming pattern."""
        naming_convention = self.cleaned_data.get('naming_convention')
        custom_pattern = self.cleaned_data.get('custom_naming_pattern')
        
        if naming_convention == 'custom':
            if not custom_pattern:
                raise ValidationError('Custom naming pattern is required when "Custom" is selected.')
            
            # Validate pattern contains at least original_name
            if '{original_name}' not in custom_pattern:
                raise ValidationError('Custom pattern must include {original_name} variable.')
            
            # Check for invalid characters
            invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
            for char in invalid_chars:
                if char in custom_pattern:
                    raise ValidationError(f'Invalid character "{char}" in naming pattern.')
        
        return custom_pattern
    
    def clean_save_location(self):
        """Validate save location if provided."""
        save_location = self.cleaned_data.get('save_location')

        if save_location:
            save_location = save_location.strip()

            # Allow both absolute paths and folder names from browser picker
            if os.path.isabs(save_location):
                # Absolute path validation
                if not os.path.exists(save_location) or not os.path.isdir(save_location):
                    raise ValidationError('The specified directory does not exist or is not accessible.')
            else:
                # Folder name validation (from browser picker)
                # Check for invalid characters in folder names
                invalid_chars = ['<', '>', ':', '"', '|', '?', '*', '/', '\\']
                for char in invalid_chars:
                    if char in save_location:
                        raise ValidationError(f'Invalid character "{char}" in folder name.')

                # Check for reserved names
                reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4',
                                'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2',
                                'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
                if save_location.upper() in reserved_names:
                    raise ValidationError('The folder name is reserved and cannot be used.')

        return save_location


class PDFUploadForm(forms.Form):
    """Form for single PDF upload and signing."""
    pdf_file = forms.FileField(
        label='PDF File',
        widget=forms.FileInput(attrs={
            'accept': '.pdf',
            'class': 'form-control',
            'id': 'pdf-file',
        }),
        help_text='Select a PDF file to sign (max 10MB)'
    )
    
    signature_type = forms.ChoiceField(
        label='Signature Type',
        choices=[
            ('visible', 'Visible Signature'),
            ('invisible', 'Invisible Signature'),
        ],
        initial='visible',
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input',
        }),
        help_text='Choose whether the signature should be visible on the document'
    )
    
    apply_to_all_pages = forms.BooleanField(
        label='Apply to all pages',
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'apply-to-all-pages'
        }),
        help_text='Apply signature to all pages of the PDF'
    )
    
    def clean_pdf_file(self):
        """Validate the uploaded PDF file."""
        pdf_file = self.cleaned_data.get('pdf_file')
        
        if not pdf_file:
            raise ValidationError('Please select a PDF file.')
        
        if not pdf_file.name.lower().endswith('.pdf'):
            raise ValidationError('Only PDF files are allowed.')
            
        if pdf_file.size > 10 * 1024 * 1024:  # 10MB limit
            raise ValidationError('File size must be less than 10MB.')
            
        return pdf_file


class FolderSelectionForm(forms.Form):
    """Form for folder selection dialog."""
    selected_folder = forms.CharField(
        max_length=500,
        widget=forms.HiddenInput(),
        required=True
    )
