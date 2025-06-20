# Digital Workspace - Django Web Application

A modular Django web application with tile-based dashboard architecture, featuring user authentication, PDF digital signature functionality, and REST API endpoints.

## 🚀 Features

### Authentication System
- **Secure User Authentication**: Django's built-in authentication with custom views
- **Session Management**: Automatic session expiry and secure cookie handling
- **User Registration**: New user account creation with validation
- **Login/Logout**: Secure authentication flow with proper redirects

### Dashboard
- **Tile-Based Layout**: Modular dashboard design for easy app expansion
- **User Statistics**: Display user information and activity stats
- **Responsive Design**: Bootstrap-powered responsive interface
- **Application Cards**: Visual representation of available applications

### PDF Digital Signature
- **Cryptographic Signatures**: Industry-standard X.509 certificate-based digital signatures
- **File Upload**: Secure PDF file upload with validation
- **Digital Signing**: Cryptographic signature with timestamp and location
- **Signature Verification**: Verify authenticity and integrity of signed documents
- **Document Integrity**: Hash-based tamper detection
- **Certificate Management**: Self-signed X.509 certificates for M.ARUL
- **Chennai GMT Timezone**: Accurate timestamp with local timezone
- **Secure Download**: Protected file download with access controls

### REST API
- **Authentication Endpoints**: Login/logout via API
- **PDF Processing API**: Upload and sign PDFs programmatically
- **Rate Limiting**: Built-in throttling for API security
- **JSON Responses**: Standardized API response format

## 🛠️ Technical Stack

- **Backend**: Django 5.2.1
- **Frontend**: Bootstrap 5.3 + HTMX
- **Database**: SQLite (development)
- **PDF Processing**: ReportLab + PyPDF2 + Cryptography
- **Digital Signatures**: X.509 certificates with cryptographic validation
- **API**: Django REST Framework
- **Authentication**: Django's built-in auth system

## 📋 Prerequisites

- Python 3.10.6 or higher
- pip (Python package installer)
- Virtual environment support

## ⚙️ Installation & Setup

### 1. Clone and Navigate
```bash
cd D:\FTE  # or your project directory
```

### 2. Virtual Environment
```bash
# Create virtual environment
py -m venv django_env

# Activate virtual environment
django_env\Scripts\activate  # Windows
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Database Setup
```bash
python manage.py migrate
```

### 5. Create Admin Users
```bash
python create_superuser.py
```

### 6. Run Development Server
```bash
python manage.py runserver
```

## 👥 User Accounts

### Default Admin Users
- **Username**: `admin` | **Password**: `primary`
- **Username**: `FTEadmin` | **Password**: `primary`

Both users have superuser privileges and full access to all features.

## 🔐 Security Features

### Authentication Requirements
- All views require user login except authentication pages
- `LoginRequiredMixin` applied to all protected views
- Automatic redirect to login page for unauthenticated users
- Session timeout after 1 hour of inactivity

### Security Headers
- XSS protection enabled
- Content type sniffing protection
- Frame options set to DENY
- Secure session cookies (HTTP-only)

### File Security
- File type validation (PDF only)
- File size limits (10MB maximum)
- Secure file paths and access controls
- User-specific file naming

## 📁 Project Structure

```
digital_workspace/
├── authentication/          # User authentication app
├── dashboard/              # Main dashboard app
├── pdf_signature/          # PDF signing functionality
├── api/                   # REST API endpoints
├── templates/             # HTML templates
├── static/               # Static files (CSS, JS, images)
├── media/                # User uploaded files
├── logs/                 # Application logs
├── digital_workspace/    # Main project settings
└── manage.py            # Django management script
```

## 🔗 URL Structure

### Web Interface
- `/` - Home (redirects based on auth status)
- `/auth/login/` - User login
- `/auth/register/` - User registration
- `/auth/logout/` - User logout
- `/dashboard/` - Main dashboard
- `/pdf-signature/` - PDF signature application
- `/pdf-signature/verify/` - PDF signature verification
- `/admin/` - Django admin interface

### API Endpoints
- `/api/auth/login/` - API login
- `/api/auth/logout/` - API logout
- `/api/pdf/upload/` - PDF upload and signing

## 📱 Usage Guide

### Web Interface
1. **Login**: Navigate to the application and log in with admin credentials
2. **Dashboard**: View available applications in tile format
3. **PDF Signing**: Click on PDF Digital Signature tile
4. **Upload**: Select a PDF file and click "Sign PDF"
5. **Download**: Download the cryptographically signed PDF
6. **Verification**: Click "Verify PDF Signature" to validate any signed document
7. **Results**: View detailed verification results including signature validity and document integrity

### API Usage
```bash
# Login via API
curl -X POST http://127.0.0.1:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "primary"}'

# Upload PDF via API
curl -X POST http://127.0.0.1:8000/api/pdf/upload/ \
  -H "X-CSRFToken: [token]" \
  -F "pdf_file=@sample.pdf"
```

## 🔧 Configuration

### Environment Settings
- **DEBUG**: Set to `False` in production
- **SECRET_KEY**: Change in production
- **ALLOWED_HOSTS**: Configure for production domain
- **DATABASE**: Switch to PostgreSQL/MySQL for production

### Logging
- Application logs stored in `logs/django.log`
- Separate loggers for each app module
- Configurable log levels and formats

## 🚀 Deployment Notes

### Production Checklist
- [ ] Set `DEBUG = False`
- [ ] Configure production database
- [ ] Set up proper static file serving
- [ ] Enable HTTPS and secure cookies
- [ ] Configure email backend
- [ ] Set up proper logging
- [ ] Configure backup strategy

## 🤝 Contributing

This project follows Django best practices and modular architecture for easy expansion:

1. **Adding New Apps**: Create new Django apps and add tiles to dashboard
2. **Code Style**: Follow PEP 8 and Django conventions
3. **Security**: Always use `LoginRequiredMixin` for protected views
4. **Testing**: Write tests for new functionality

## 📞 Support

For technical support or questions about the Digital Workspace application, please refer to the Django documentation or contact the development team.

---

**Digital Workspace** - A secure, modular Django application for document processing and management.
