import logging
import json

# log initiation
logger = logging.getLogger()

# log level
logger.setLevel(logging.ERROR)

# log format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)