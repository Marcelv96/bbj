import os
import pymysql
from pathlib import Path
from dotenv import load_dotenv

# 1. Setup Paths
BASE_DIR = Path(__file__).resolve().parent.parent

# 2. Load .env (Absolute path is required for PythonAnywhere)
env_path = BASE_DIR / '.env'
load_dotenv(dotenv_path=env_path)

# 3. Django 6 Compatibility
pymysql.version_info = (2, 2, 1, "final", 0)
pymysql.install_as_MySQLdb()

# --- SECURITY ---
SECRET_KEY = os.getenv('SECRET_KEY', 'fallback-key-for-dev-only')
DEBUG = True #os.getenv('DEBUG', 'False') == 'True'

# Restricted hosts for production security
hosts = os.getenv('ALLOWED_HOSTS', 'bookinsapp.pythonanywhere.com')
ALLOWED_HOSTS = [h.strip() for h in hosts.split(',') if h]

# --- APPLICATION DEFINITION ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.sites',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'imagekit',
    'compressor',
    'bookingApp',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'bookingProject.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'bookingApp.context_processors.pending_appointments_count',
            ],
        },
    },
]

WSGI_APPLICATION = 'bookingProject.wsgi.application'

# --- DATABASE ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME'),
        'USER': os.getenv('DB_USER'),
        'PASSWORD': os.getenv('DB_PASSWORD'),
        'HOST': os.getenv('DB_HOST'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'", # Removed innodb_strict_mode
            'charset': 'utf8mb4',
        },
    }
}

# -------------------------
# AUTHENTICATION (FIXED)
# -------------------------

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = 'login_dispatch'
LOGOUT_REDIRECT_URL = 'login'
LOGOUT_ON_GET = True

# -------------------------
# ALLAUTH – SAFE CONFIG
# -------------------------

ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_PASSWORD_REQUIRED = False


ACCOUNT_LOGIN_ON_PASSWORD_RESET = True
ACCOUNT_PREVENT_ENUMERATION = True

# Signup fields (Django 6 compliant)
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']

# -------------------------
# SOCIAL AUTH (GOOGLE)
# -------------------------

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    }
}

# IMPORTANT FIXES
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'

# Keep password auth ALWAYS enabled
SOCIALACCOUNT_ADAPTER = 'bookingApp.adapters.SafeSocialAccountAdapter'

SITE_ID = int(os.getenv('SITE_ID', 7))
SITE_URL = os.getenv(
    'SITE_URL',
    'https://bookinsapp.pythonanywhere.com'
)


# --- STATIC & MEDIA ---
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# Fixes (staticfiles.W004)

STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# --- COMPRESSOR ---
COMPRESS_ENABLED = True
COMPRESS_OFFLINE = not DEBUG
COMPRESS_CSS_FILTERS = [
    'compressor.filters.css_default.CssAbsoluteFilter',
    'compressor.filters.cssmin.CSSMinFilter',
]
COMPRESS_JS_FILTERS = ['compressor.filters.jsmin.JSMinFilter']

# --- EMAIL ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER


# PayFast Account Settings
PAYFAST_MERCHANT_ID = os.getenv('PAYFAST_MERCHANT_ID')
PAYFAST_MERCHANT_KEY = os.getenv('PAYFAST_MERCHANT_KEY')
PAYFAST_PASSPHRASE = os.getenv('PAYFAST_PASSPHRASE')
PAYFAST_URL = os.getenv('PAYFAST_URL', 'https://www.payfast.co.za/eng/process')


# Change this to ALLOWALL to allow any site to embed your booking form


# --- LOCALIZATION ---
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Johannesburg'
USE_I18N = True
USE_TZ = True
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


X_FRAME_OPTIONS = 'ALLOWALL'
CSP_FRAME_ANCESTORS = ("*",)

# This allows the CSRF token to be "seen" by the browser from another site
CSRF_COOKIE_SAMESITE = 'None'
CSRF_COOKIE_SECURE = True

# This allows logins/sessions to work inside the iframe
SESSION_COOKIE_SAMESITE = 'None'
SESSION_COOKIE_SECURE = True

# Explicitly trust your domain for cross-site POSTs
CSRF_TRUSTED_ORIGINS = [
    'https://bookinsapp.pythonanywhere.com','https://getmebooked.co.za',
]
# --- PRODUCTION SECURITY ---
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

if not DEBUG:
    # SSL/HTTPS Redirects
    SECURE_SSL_REDIRECT = True

    # HSTS (Strict Transport Security)
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Cookies Security
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True

    CSRF_COOKIE_SAMESITE = 'None'
    CSRF_TRUSTED_ORIGINS = [
        'https://bookinsapp.pythonanywhere.com',
        'https://getmebooked.co.za',
        'https://www.getmebooked.co.za',
    ]
    X_FRAME_OPTIONS = 'ALLOWALL'
    CSP_FRAME_ANCESTORS = ("*",) # Or list specific domains

    # If you use sessions/login inside the iframe, add this too
    SESSION_COOKIE_SAMESITE = 'None'

    # Browser Protection
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"