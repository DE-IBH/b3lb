import environ

# reading .env file
env = environ.Env()
environ.Env.read_env(env.str('ENV_FILE', default='.env'))


######
# B3LB Base Settings
######

B3LB_API_BASE_DOMAIN = env.str('B3LB_API_BASE_DOMAIN')

B3LB_ALLOWED_SHA_ALGORITHMS = env.list('B3LB_ALLOWED_SHA_ALGORITHMS', default=["sha1", "sha256", "sha384", "sha512"])
B3LB_NODE_PROTOCOL = env.str('B3LB_NODE_PROTOCOL', default='https://')
B3LB_NODE_DEFAULT_DOMAIN = env.str('B3LB_NODE_DEFAULT_DOMAIN', default='bbbconf.de')
B3LB_NODE_BBB_ENDPOINT = env.str('B3LB_NODE_BBB_ENDPOINT', default='bigbluebutton/api/')
B3LB_NODE_LOAD_ENDPOINT = env.str('B3LB_NODE_LOAD_ENDPOINT', default='b3lb/load')
B3LB_NODE_REQUEST_TIMEOUT = env.int('B3LB_NODE_REQUEST_TIMEOUT', default=5)

B3LB_NO_SLIDES_TEXT = env.str('B3LB_NO_SLIDES_TEXT', default='<default>')

B3LB_CACHE_NML_PATTERN = env.str('B3LB_CACHE_NML_PATTERN', default='NML#{}')
B3LB_CACHE_NML_TIMEOUT = env.int('B3LB_CACHE_NML_TIMEOUT', default=30)

B3LB_API_MATE_BASE_URL = env.str('B3LB_API_MATE_BASE_URL', default='https://mconf.github.io/api-mate/')
B3LB_API_MATE_PW_LENGTH = env.int('B3LB_API_MATE_PW_LENGTH', default=13)

######
# B3LB Storage Setting
######

B3LB_RECORD_META_DATA_TAG = env.str("B3LB_RECORD_META_DATA_TAG", default="b3lb-recordset")
B3LB_RENDERING = env.bool("B3LB_RENDERING", default=False)
B3LB_RECORD_STORAGE = env.str('B3LB_RECORD_STORAGE', default='local')
B3LB_S3_ACCESS_KEY = env.str('B3LB_S3_ACCESS_KEY', default=env.str('AWS_S3_ACCESS_KEY_ID', default=env.str('AWS_S3_SECRET_ACCESS_KEY', default='')))
B3LB_S3_BUCKET_NAME = env.str('B3LB_S3_BUCKET_NAME', 'raw')
B3LB_S3_ENDPOINT_URL = env.str('B3LB_S3_ENDPOINT_URL', default=env.str('AWS_S3_ENDPOINT_URL', default=''))
B3LB_S3_SECRET_KEY = env.str('B3LB_S3_SECRET_KEY', default=env.str('AWS_ACCESS_KEY_ID', default=env.str('AWS_SECRET_ACCESS_KEY', default='')))
B3LB_S3_URL_PROTOCOL = env.str('B3LB_S3_URL_PROTOCOL', default=env.str('AWS_S3_URL_PROTOCOL', default='https:'))

# Filesystem configuration
# max len is 26
# HIERARCHY_LEN * HIERARCHY_DEPTH < 26
B3LB_RECORD_PATH_HIERARCHY_WIDTH = env.int('B3LB_RECORD_PATH_HIERARCHY_WIDTH', default=2)
B3LB_RECORD_PATH_HIERARCHY_DEPHT = env.int('B3LB_RECORD_PATH_HIERARCHY_DEPHT', default=3)

######
# B3LB Celery Settings
######
B3LB_RECORD_TASK_TEMPLATE_FOLDER = env.path("B3LB_RECORD_TASK_TEMPLATE_FOLDER", default="/templates").root
B3LB_TASK_QUEUE_CORE = env.str("B3LB_TASK_QUEUE_CORE", default="b3lb")
B3LB_TASK_QUEUE_HOUSEKEEPING = env.str("B3LB_TASK_QUEUE_HOUSEKEEPING", default="b3lb")
B3LB_TASK_QUEUE_RECORD = env.str("B3LB_TASK_QUEUE_RECORD", default="b3lb")
B3LB_TASK_QUEUE_STATISTICS = env.str("B3LB_TASK_QUEUE_STATISTICS", default="b3lb")
