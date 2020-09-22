import os

if 'MONGODB_URI' in os.environ:
    if '?' not in os.environ['MONGODB_URI']:
        MONGO_URI = f'{os.environ["MONGODB_URI"]}/ex2dev?authSource=admin'
    else:
        MONGO_URI = os.environ["MONGODB_URI"]
else:
    MONGO_URI = 'mongodb://localhost:27017/ex2dev'

if 'REDIS_URI' in os.environ:
    REDIS_URI = os.environ['REDIS_URI']
else:
    REDIS_URI = None

if 'PUBLIC_HOSTNAME' in os.environ:
    value = os.environ['PUBLIC_HOSTNAME']
    if value.startswith('.'):
        value = value[1:]
    BASE_URL = 'https://' + value
else:
    BASE_URL = 'http://localhost:5000'

GOOGLE_ANALYTICS_ID = None

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
