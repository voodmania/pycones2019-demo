from starlette.config import Config


config = Config('.env')


AUDIT = config("AUDIT", cast=bool, default=False)

LOGGER_LEVEL = config("LOGGER_LEVEL", default="INFO")
LOGGER_FILE = config("LOGGER_FILE")

REQUEST_TIMEOUT = config("REQUEST_TIMEOUT", cast=float, default=30.0)
REDIS_TIMEOUT = config("REDIS_TIMEOUT", cast=float, default=0.2)
POSTGRES_TIMEOUT = config("POSTGRES_TIMEOUT", cast=float, default=0.2)

REDIS_URL = config("REDIS_URL", default="redis://redis")

PG_USER = config("PG_USER", default="postgres")
PG_PASS = config("PG_PASS", default="postgres")
PG_DATABASE = config("PG_DATABASE", default="test")
PG_HOST = config("PG_HOST", default="postgres")
PG_PORT = config("PG_PORT", default=5432, cast=int)
