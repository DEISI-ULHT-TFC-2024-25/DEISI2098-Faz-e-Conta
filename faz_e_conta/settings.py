import os
from pathlib import Path

# Caminho base do projeto
BASE_DIR = Path(__file__).resolve().parent.parent

# Segurança
SECRET_KEY = 'django-insecure-f$+5$)1vhn7)%naj2ami^i44t1m)h=pzdee!wl+x$z7)405!&p'
DEBUG = True
ALLOWED_HOSTS = ['*']  # Permite acesso a partir de qualquer IP (desenvolvimento)

# Aplicações instaladas
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'data_hub',  # a tua app
]

# Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# URLs
ROOT_URLCONF = 'faz_e_conta.urls'

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],  # Adiciona aqui se tiveres templates fora da app
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

WSGI_APPLICATION = 'faz_e_conta.wsgi.application'

# Base de dados
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Validação de passwords
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Internacionalização
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Ficheiros estáticos (CSS, JS, imagens)
STATIC_URL = 'static/'

# Diretório onde os ficheiros estáticos do projeto ficam guardados durante o desenvolvimento
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Diretório onde serão colocados os ficheiros estáticos para produção com collectstatic
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Ficheiros media (uploads e imagens geradas pelo utilizador ou pelo sistema)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'faz_e_conta/resources/')

# Primary key padrão
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
