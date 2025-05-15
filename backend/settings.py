from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
import os

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-l3t17j@t&60hwwa8ze7^$10zui4ca2!!k^**0h%ujxncmtg^(*'

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'corsheaders',  
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'apis',
    'rest_framework',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware', 
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.urls'
MEDIA_URL = '/chat_attachments/'  # ← الجزء الأول من المسار
MEDIA_ROOT = os.path.join(BASE_DIR, 'chat_attachments')
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],  
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

import os

DATABASES = {
    'default': {
        # استخدم محرك PostgreSQL العادي
        'ENGINE': 'django.db.backends.postgresql',
        # البيانات تأتي من متغيرات البيئة، مع قيم افتراضية للعرض فقط
        'NAME': os.environ.get('DB_NAME', 'wejhatidb'),
        'USER': os.environ.get('DB_USER', 'nahari'),
        'PASSWORD': os.environ.get('DB_PASSWORD', '••••••••••••••••••••••••••'),
        'HOST': os.environ.get('DB_HOST', 'dpg-d0j4u8ili9vc73bam73g-a'),
        'PORT': os.environ.get('DB_PORT', '5432'),

        # تحسينات الأداء
        'CONN_MAX_AGE': 300,           # إبقاء الاتصال مفتوحًا لمدة 300 ثانية
        'OPTIONS': {
            'connect_timeout': 30,     # مهلة الاتصال 30 ثانية
        },
    }
}


AUTH_USER_MODEL = 'auth.User' 
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True  
