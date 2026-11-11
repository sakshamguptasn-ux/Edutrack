import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'edutrack-dev-secret-key-change-in-production')
    DATABASE = os.path.join(BASE_DIR, 'database', 'edutrack.db')
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'ppt', 'pptx'}
    FACULTY_PASSCODE = os.environ.get('FACULTY_PASSCODE', 'FACULTY@EDU2026')
