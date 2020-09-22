import os

if 'REDIS_URI' in os.environ:
    REDIS_URI = os.environ['REDIS_URI']
else:
    REDIS_URI = None

MONGO_URI = 'mongodb://localhost:27017/ex2test'
PORT = 10011

BASE_URL = '*'

if 'GOOGLE_ANALYTICS_ID' in os.environ:
    GOOGLE_ANALYTICS_ID = os.environ['GOOGLE_ANALYTICS_ID']
else:
    GOOGLE_ANALYTICS_ID = None

if 'ASOBANN_DEBUG_HANDLER_WAIT' in os.environ:
    DEBUG_HANDLER_WAIT = os.environ['ASOBANN_DEBUG_HANDLER_WAIT']

if 'UPLOADED_IMAGE_STORE' in os.environ:
    UPLOADED_IMAGE_STORE = os.environ['UPLOADED_IMAGE_STORE']
else:
    UPLOADED_IMAGE_STORE = 'local'

use_aws = UPLOADED_IMAGE_STORE.lower() == 's3'
if use_aws:
    AWS_KEY = os.environ['AWS_KEY']
    AWS_SECRET = os.environ['AWS_SECRET']
    AWS_REGION = os.environ['AWS_REGION']
    AWS_S3_IMAGE_BUCKET_NAME = os.environ['AWS_S3_IMAGE_BUCKET_NAME']
else:
    AWS_KEY = None
    AWS_SECRET = None
