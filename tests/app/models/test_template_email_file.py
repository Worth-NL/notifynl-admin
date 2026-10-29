from uuid import uuid4

from botocore.exceptions import ClientError
from notifications_utils.clients.minio import client as minio_client

from app.models.template_email_file import TemplateEmailFile, upload_template_email_file_to_s3
from tests.conftest import SERVICE_ONE_ID


# [NOTIFYNL] S3 is MinIO (the CI job has a minio service), not moto's in-memory AWS:
# notifications_utils.s3 and TemplateEmailFile.size talk to MINIO_URL.
def test_get_metadata_from_uploaded_file(notify_admin, fake_uuid):
    s3 = minio_client("s3")
    bucket_name = "test-template-email-files"
    key = f"{SERVICE_ONE_ID}/{fake_uuid}"
    try:
        s3.create_bucket(Bucket=bucket_name)
    except ClientError:
        pass

    upload_template_email_file_to_s3(b"hello", key)
    try:
        template_email_file = TemplateEmailFile(
            {
                "service_id": SERVICE_ONE_ID,
                "template_id": str(uuid4()),
                "id": fake_uuid,
                "filename": "example.pdf",
                "created_by_id": str(uuid4()),
                "retention_period": 78,
                "validate_users_email": True,
            }
        )
        assert template_email_file.size == 5 == len("hello")
        assert template_email_file.file_contents.read() == b"hello"
        assert template_email_file.extension == "pdf"
        assert template_email_file.mimetype == "application/pdf"
    finally:
        s3.delete_object(Bucket=bucket_name, Key=key)
