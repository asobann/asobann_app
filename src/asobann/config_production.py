import os

import asobann.config_common as common

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

UPLOADED_IMAGE_STORE = common.UPLOADED_IMAGE_STORE
AWS_KEY = common.AWS_KEY
AWS_SECRET = common.AWS_SECRET
AWS_REGION = common.AWS_REGION
AWS_S3_IMAGE_BUCKET_NAME = common.AWS_S3_IMAGE_BUCKET_NAME

ACCESS_LOG = True
