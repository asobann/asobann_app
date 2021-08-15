import os

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
    AWS_REGION = None
    AWS_S3_IMAGE_BUCKET_NAME = None
