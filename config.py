import os


class Config:
    # Database URL from environment (supports sqlite/mysql/postgres). Fallback to local sqlite file.
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///optica.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Do NOT hardcode secrets in source. Provide via env var, fallback to a dev-safe default.
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-change-me')