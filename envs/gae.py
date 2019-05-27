from datetime import timedelta


MYSQL_HOST = '/cloudsql/{}'.format('<<host>>')
MYSQL_DBNAME = 'cslt'
MYSQL_USER = 'root'
MYSQL_PWD = '<<password>>'
SECRET_KEY = '<<secret_key>>'

STATIC_URL = 'https://storage.googleapis.com/cslt-211408.appspot.com/static/'
MEDIA_ROOT = ''
MEDIA_URL = 'media/'
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

DEBUG = True

TARGET_TRAINING_COUNT = 50
PENDING_APPROVAL_LIMIT = 5
MINIMUM_REVIEWS = 3
ONE_GLOSS_RECORDING_LIMIT = 2
