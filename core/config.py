import os

from dotenv import load_dotenv

load_dotenv()


SQLITE_URL = os.getenv("SQLITE_URL")
REDIS_URL = os.getenv("REDIS_URL")
