import os

RAISE = object()


def from_env(key, default=RAISE):
    if key in os.environ:
        return os.environ[key]
    else:
        if default == RAISE:
            raise ValueError(f'key {key} is not found in os.environ')
        return default


REDIS_URI = from_env('REDIS_URI', default=None)

UPLOADED_IMAGE_STORE = from_env('UPLOADED_IMAGE_STORE', default='local')

use_aws = UPLOADED_IMAGE_STORE.lower() == 's3'
if use_aws:
    AWS_KEY = from_env('AWS_KEY')
    AWS_SECRET = from_env('AWS_SECRET')
    AWS_REGION = from_env('AWS_REGION')
    AWS_S3_IMAGE_BUCKET_NAME = from_env('AWS_S3_IMAGE_BUCKET_NAME')
else:
    AWS_KEY = None
    AWS_SECRET = None
    AWS_REGION = None
    AWS_S3_IMAGE_BUCKET_NAME = None
