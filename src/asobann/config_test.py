import os

import asobann.config_common as common

REDIS_URI = common.REDIS_URI
MONGO_URI = 'mongodb://localhost:27017/ex2test'
PORT = 10011

BASE_URL = '*'

if 'GOOGLE_ANALYTICS_ID' in os.environ:
    GOOGLE_ANALYTICS_ID = os.environ['GOOGLE_ANALYTICS_ID']
else:
    GOOGLE_ANALYTICS_ID = None

if 'ASOBANN_DEBUG_HANDLER_WAIT' in os.environ:
    DEBUG_HANDLER_WAIT = os.environ['ASOBANN_DEBUG_HANDLER_WAIT']

UPLOADED_IMAGE_STORE = common.UPLOADED_IMAGE_STORE
AWS_KEY = common.AWS_KEY
AWS_SECRET = common.AWS_SECRET
AWS_REGION = common.AWS_REGION
AWS_S3_IMAGE_BUCKET_NAME = common.AWS_S3_IMAGE_BUCKET_NAME

if 'ASOBANN_DEBUG_OPTS' in os.environ:
    opts = os.environ['ASOBANN_DEBUG_OPTS'].split(',')
    DEBUG_PERFORMANCE_RECORDING = 'PERFORMANCE_RECORDING' in opts
    DEBUG_ORDER_OF_UPDATES = 'ORDER_OF_UPDATES' in opts
    DEBUG_LOG = 'LOG' in opts

if "ASOBANN_ACCESS_LOG" in os.environ:
    ACCESS_LOG = True
else:
    ACCESS_LOG = False
