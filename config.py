import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Application configuration settings."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'careerconnect-super-secret-key-2026')
    DATABASE_PATH = os.environ.get('DATABASE_PATH', os.path.join(BASE_DIR, 'careerconnect.db'))
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'resumes')
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max file upload size
