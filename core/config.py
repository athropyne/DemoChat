import os

from dotenv import load_dotenv

load_dotenv()


SQLITE_URL = os.getenv("SQLITE_URL")
PG_URL = os.getenv("PG_URL")
REDIS_URL = os.getenv("REDIS_URL")
