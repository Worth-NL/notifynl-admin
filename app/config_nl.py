"""
Configuration overrides for NotifyNL
"""

import os

from config import Config as ConfigUK

NL_PREFIX = "notifynl"


class Development(ConfigUK):
    NOTIFY_ENVIRONMENT = "development"

    SERVER_NAME = os.getenv("SERVER_NAME")
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    SESSION_PROTECTION = None

    S3_BUCKET_CSV_UPLOAD = "development-notifications-csv-upload"
    S3_BUCKET_CONTACT_LIST_UPLOAD = "development-contact-list"
    S3_BUCKET_LOGO_UPLOAD = "public-logos-tools"
    S3_BUCKET_MOU = "notify.tools-mou"
    S3_BUCKET_TRANSIENT_UPLOADED_LETTERS = "development-transient-uploaded-letters"
    S3_BUCKET_PRECOMPILED_ORIGINALS_BACKUP_LETTERS = "development-letters-precompiled-originals-backup"
    S3_BUCKET_LETTER_ATTACHMENTS = "development-letter-attachments"
    S3_BUCKET_REPORT_REQUESTS_DOWNLOAD = "development-report-requests-download"

    LOGO_CDN_DOMAIN = "static-logos.notify.tools"

    ADMIN_CLIENT_SECRET = "dev-notify-secret-key"
    DANGEROUS_SALT = "dev-notify-salt"
    SECRET_KEY = "dev-notify-secret-key"
    API_HOST_NAME = os.environ.get("API_HOST_NAME", "http://localhost:6011")
    ANTIVIRUS_API_HOST = os.environ.get("ANTIVIRUS_API_HOST", "http://localhost:6016")
    ANTIVIRUS_API_KEY = "test-key"
    ANTIVIRUS_ENABLED = os.getenv("ANTIVIRUS_ENABLED") == "1"

    ASSET_PATH = "/static/"

    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    REDIS_ENABLED = os.environ.get("REDIS_ENABLED") == "1"


class Test(Development):
    NOTIFY_ENVIRONMENT = "test"

    DEBUG = True
    TESTING = True
    WTF_CSRF_ENABLED = False

    S3_BUCKET_CSV_UPLOAD = "test-notifications-csv-upload"
    S3_BUCKET_CONTACT_LIST_UPLOAD = "test-contact-list"
    S3_BUCKET_LOGO_UPLOAD = "public-logos-test"
    S3_BUCKET_MOU = "test-mou"
    S3_BUCKET_TRANSIENT_UPLOADED_LETTERS = "test-transient-uploaded-letters"
    S3_BUCKET_PRECOMPILED_ORIGINALS_BACKUP_LETTERS = "test-letters-precompiled-originals-backup"
    S3_BUCKET_LETTER_ATTACHMENTS = "test-letter-attachments"
    S3_BUCKET_REPORT_REQUESTS_DOWNLOAD = "test-report-requests-download"

    LOGO_CDN_DOMAIN = "static-logos.test.com"
    API_HOST_NAME = "http://you-forgot-to-mock-an-api-call-to"
    TEMPLATE_PREVIEW_API_HOST = "http://localhost:9999"
    ANTIVIRUS_API_HOST = "https://test-antivirus"
    ANTIVIRUS_API_KEY = "test-antivirus-secret"
    ANTIVIRUS_ENABLED = True

    ASSET_DOMAIN = "static.example.com"
    ASSET_PATH = "https://static.example.com/"


class Acceptance(ConfigUK):
    NOTIFY_ENVIRONMENT = "acceptance"

    S3_BUCKET_CSV_UPLOAD = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-notifications-csv-upload"
    S3_BUCKET_CONTACT_LIST_UPLOAD = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-contact-list"
    S3_BUCKET_LOGO_UPLOAD = f"{NL_PREFIX}-acc-public-logos-tools"
    S3_BUCKET_MOU = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-mou"
    S3_BUCKET_TRANSIENT_UPLOADED_LETTERS = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-transient-uploaded-letters"
    S3_BUCKET_PRECOMPILED_ORIGINALS_BACKUP_LETTERS = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-precompiled-originals-backup"
    S3_BUCKET_LETTER_ATTACHMENTS = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-attachments"
    S3_BUCKET_REPORT_REQUESTS_DOWNLOAD = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-report-requests-download"


class Production(ConfigUK):
    NOTIFY_ENVIRONMENT = "production"

    S3_BUCKET_CSV_UPLOAD = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-notifications-csv-upload"
    S3_BUCKET_CONTACT_LIST_UPLOAD = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-contact-list"
    S3_BUCKET_LOGO_UPLOAD = f"{NL_PREFIX}-prod-public-logos-tools"
    S3_BUCKET_MOU = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-mou"
    S3_BUCKET_TRANSIENT_UPLOADED_LETTERS = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-transient-uploaded-letters"
    S3_BUCKET_PRECOMPILED_ORIGINALS_BACKUP_LETTERS = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-precompiled-originals-backup"
    S3_BUCKET_LETTER_ATTACHMENTS = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-attachments"
    S3_BUCKET_REPORT_REQUESTS_DOWNLOAD = f"{NL_PREFIX}-{NOTIFY_ENVIRONMENT}-report-requests-download"
