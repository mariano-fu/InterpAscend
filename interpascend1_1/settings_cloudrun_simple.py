"""
Simplified Django settings for Cloud Run deployment using SQLite.
This avoids PostgreSQL complexity and should resolve your current issues.
"""

import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Helper to read env-vars or raise an error
def get_env_variable(name: str) -> str:
    """Raise an error if the variable isn't set."""
    try:
        return os.environ[name]
    except KeyError:
        raise ImproperlyConfigured(f"Missing required environment variable: {name}")

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECRET_KEY from environment (required in production)
SECRET_KEY = get_env_variable("DJANGO_SECRET_KEY")

# DEBUG mode from environment (default False)
DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() in ("1", "true", "yes")

# Hosts allowed to serve the application
ALLOWED_HOSTS = os.getenv(
    "DJANGO_ALLOWED_HOSTS",
    "localhost,127.0.0.1,interpascend-859601129052.us-central1.run.app,interpascend.com,www.interpascend.com"
).split(",")

# CSRF Trusted Origins
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'https://interpascend-859601129052.us-central1.run.app',
    'https://interpascend.com',
    'https://www.interpascend.com'
]

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',
    'terminology',
    'srs',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Security settings - FIXED: Only secure cookies on HTTPS
CSRF_COOKIE_SECURE = not DEBUG  # Only secure in production
SESSION_COOKIE_SECURE = not DEBUG  # Only secure in production

ROOT_URLCONF = 'interpascend1_1.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.template.context_processors.debug',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'interpascend1_1.context_processors.ga_settings',
            ],
        },
    },
]

WSGI_APPLICATION = 'interpascend1_1.wsgi.application'

# SIMPLIFIED: Always use SQLite (even on Cloud Run)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = []
STATIC_ROOT = BASE_DIR / "staticfiles"

# WhiteNoise: compress & cache static files efficiently
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Media files (Uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Google Analytics ID
GA_ID = os.getenv('GA_ID', 'G-PD9VYGR641')

# Authentication settings
LOGIN_URL = '/srs/login/'
LOGIN_REDIRECT_URL = '/srs/'
LOGOUT_REDIRECT_URL = '/terminology/translate/'