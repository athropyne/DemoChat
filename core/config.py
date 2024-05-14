import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


SQLITE_URL = os.getenv("SQLITE_URL")
PG_URL = os.getenv("PG_URL")

TOKEN_KEY = os.getenv("TOKEN_KEY")
TOKEN_EXPIRE = timedelta(minutes=15)
