# PDF Signature Tool

A Django-based web application for digitally signing and verifying PDF documents with support for Adobe and Edge browser compatibility.

## Features

- **Digital Signing**: Sign PDF documents with cryptographic signatures
- **Multi-page Support**: Sign all pages of a multi-page PDF document
- **Signature Verification**: Verify the authenticity of signed PDFs
- **Batch Processing**: Sign multiple PDFs at once
- **Browser Compatibility**: Works with Adobe Reader and Microsoft Edge
- **User Authentication**: Secure user authentication and session management
- **Responsive Design**: Works on desktop and mobile devices

## Prerequisites

- Python 3.8+
- Django 4.0+
- endesive
- cryptography
- PyPDF2
- django-crispy-forms (for form rendering)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd pdf-signature-tool
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Run migrations:
   ```bash
   python manage.py migrate
   ```

5. Create a superuser (optional):
   ```bash
   python manage.py createsuperuser
   ```

6. Run the development server:
   ```bash
   python manage.py runserver
   ```

7. Access the application at http://127.0.0.1:8000/

## Usage

### Signing a PDF

1. Navigate to the home page
2. Click "Sign PDF"
3. Upload your PDF file
4. Select signature type (visible or invisible)
5. Choose whether to apply the signature to all pages
6. Click "Sign PDF"
7. Download the signed PDF when processing is complete

### Verifying a Signed PDF

1. Navigate to the "Verify Signature" page
2. Upload the signed PDF file
3. Click "Verify Signature"
4. View the verification results

### Batch Processing

1. Navigate to the "Batch Sign" page
2. Upload multiple PDF files
3. Configure signing options
4. Click "Start Batch Process"
5. Monitor the progress of the batch job
6. Download the signed files when complete

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1
MEDIA_ROOT=media/
STATIC_ROOT=staticfiles/
STATIC_URL=/static/
```

### Certificate Configuration

The application will automatically generate a self-signed certificate for testing purposes. For production use, you should:

1. Obtain a valid code signing certificate from a trusted Certificate Authority (CA)
2. Place the certificate files in the `certs/` directory
3. Update the certificate paths in `settings.py`

## Security Considerations

- Always use HTTPS in production
- Store sensitive information in environment variables
- Regularly update dependencies
- Use a strong secret key
- Implement proper user authentication and authorization
- Limit file upload sizes
- Validate all user inputs

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support, please open an issue in the GitHub repository or contact the development team.
