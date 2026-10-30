from botocore.exceptions import ClientError
from notifications_utils.clients.minio import client as minio_client

from app.models.report_request import ReportRequest

REPORT_KEY = "notifications_report/abcd.csv"


def _ensure_empty_bucket(s3, bucket_name):
    try:
        s3.create_bucket(Bucket=bucket_name)
    except ClientError:
        pass
    for obj in s3.list_objects_v2(Bucket=bucket_name).get("Contents", []):
        s3.delete_object(Bucket=bucket_name, Key=obj["Key"])


def test_report_request_download(notify_admin):
    s3 = minio_client("s3")
    bucket_name = ReportRequest.get_bucket_name()
    _ensure_empty_bucket(s3, bucket_name)
    s3.put_object(Bucket=bucket_name, Key=REPORT_KEY, Body=b"csv_content")

    try:
        csv_file = ReportRequest.download("abcd")
        assert csv_file.read().decode("utf-8") == "csv_content"
    finally:
        s3.delete_object(Bucket=bucket_name, Key=REPORT_KEY)


def test_exists_in_s3_should_return_true_when_report_exists(notify_admin):
    s3 = minio_client("s3")
    bucket_name = ReportRequest.get_bucket_name()
    _ensure_empty_bucket(s3, bucket_name)
    s3.put_object(Bucket=bucket_name, Key=REPORT_KEY, Body=b"csv_content")

    try:
        assert ReportRequest.exists_in_s3("abcd")
    finally:
        s3.delete_object(Bucket=bucket_name, Key=REPORT_KEY)


def test_exists_in_s3_should_return_false_when_report_does_not_exist(notify_admin):
    s3 = minio_client("s3")
    bucket_name = ReportRequest.get_bucket_name()
    _ensure_empty_bucket(s3, bucket_name)

    assert ReportRequest.exists_in_s3("abcd") is False
