import asobann.config_common as common

REDIS_URI = common.REDIS_URI

value = common.from_env("MONGODB_URI")
MONGO_URI = value + ('&' if '?' in value else '?') + 'retryWrites=false'

value = common.from_env('PUBLIC_HOSTNAME')
if value.startswith('.'):
    value = value[1:]
BASE_URL = 'https://' + value

GOOGLE_ANALYTICS_ID = common.from_env('GOOGLE_ANALYTICS_ID')

UPLOADED_IMAGE_STORE = common.UPLOADED_IMAGE_STORE
AWS_KEY = common.AWS_KEY
AWS_SECRET = common.AWS_SECRET
AWS_REGION = common.AWS_REGION
AWS_S3_IMAGE_BUCKET_NAME = common.AWS_S3_IMAGE_BUCKET_NAME

AWS_COGNITO_USER_POOL_ID = common.AWS_COGNITO_USER_POOL_ID
AWS_COGNITO_CLIENT_ID = common.AWS_COGNITO_CLIENT_ID

ACCESS_LOG = True
