import os
from datetime import timedelta


MYSQL_HOST = ''
MYSQL_DBNAME = ''
MYSQL_USER = ''
MYSQL_PWD = ''
SECRET_KEY = ''

STATIC_URL = '/media/static/'
MEDIA_ROOT = os.getenv('CSLT_MEDIA_ROOT', '')
MEDIA_URL = '/media/'
SIMPLE_JWT_ACCESS_TOKEN_LIFETIME = timedelta(days=7)
SIMPLE_JWT_REFRESH_TOKEN_LIFETIME = timedelta(days=30)
SIMPLE_JWT_SLIDING_TOKEN_LIFETIME = timedelta(days=7)
SIMPLE_JWT_SLIDING_TOKEN_REFRESH_LIFETIME = timedelta(days=30)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler'
        },
    },
    'loggers': {
        '': {  # 'catch all' loggers by referencing it with the empty string
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}

DEBUG = False

TARGET_TRAINING_COUNT = 50
PENDING_APPROVAL_LIMIT = 100000
MINIMUM_REVIEWS = 3

