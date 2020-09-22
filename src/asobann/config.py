import os

if 'REDIS_URI' in os.environ:
    REDIS_URI = os.environ['REDIS_URI']
else:
    REDIS_URI = None

MONGO_URI = os.environ["MONGODB_URI"] + ('&' if '?' in os.environ["MONGODB_URI"] else '?') + 'retryWrites=false'

value = os.environ['PUBLIC_HOSTNAME']
if value.startswith('.'):
    value = value[1:]
BASE_URL = 'https://' + value

GOOGLE_ANALYTICS_ID = os.environ['GOOGLE_ANALYTICS_ID']

if 'UPLOAD_IMAGE_STORAGE' in os.environ:
    UPLOAD_IMAGE_STORAGE = os.environ['UPLOAD_IMAGE_STORAGE']
else:
    UPLOAD_IMAGE_STORAGE = 'local'

use_aws = UPLOAD_IMAGE_STORAGE.lower() == 's3'
if use_aws:
    AWS_KEY = os.environ['AWS_KEY']
    AWS_SECRET = os.environ['AWS_SECRET']
else:
    AWS_KEY = None
    AWS_SECRET = None
