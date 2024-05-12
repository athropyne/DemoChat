import hashlib
import os

import passlib.context
from pydantic import BaseModel


class PasswordManager:
    context = passlib.context.CryptContext(schemes=["bcrypt"], deprecated="auto")

    @classmethod
    def get_hash(cls, string: str):
        return cls.context.hash(string)

    @classmethod
    def verify_hash(cls, plain: str, hashed: str):
        return cls.context.verify(plain, hashed)


class Token:
    @classmethod
    def generate(cls):
        return hashlib.md5(os.urandom(32)).hexdigest()
