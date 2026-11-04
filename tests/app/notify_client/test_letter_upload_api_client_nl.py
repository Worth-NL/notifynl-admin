import base64
import uuid

from app.notify_client.letter_upload_api_client_nl import LetterUploadApiClient


def test_sanitise_letter_asks_the_api(mocker):
    client = LetterUploadApiClient(mocker.MagicMock())
    mock_post = mocker.patch(
        "app.notify_client.NotifyAdminAPIClient.post",
        return_value={"status_code": 400, "data": {"message": "address-placement-mismatch"}},
    )
    upload_id = uuid.uuid4()

    response = client.sanitise_letter("service-id", b"%PDF", upload_id=upload_id)

    assert response.status_code == 400
    assert response.json() == {"message": "address-placement-mismatch"}
    # the file only: the API decides the address window and whether international letters are allowed
    mock_post.assert_called_once_with(
        url="/service/service-id/letter-upload/sanitise",
        data={"file": base64.b64encode(b"%PDF").decode(), "upload_id": str(upload_id)},
    )


def test_get_png_for_invalid_pdf_page_asks_the_api_for_one_page(mocker):
    client = LetterUploadApiClient(mocker.MagicMock())
    mock_extract = mocker.patch(
        "app.notify_client.letter_upload_api_client_nl.extract_page_from_pdf", return_value=b"page 2"
    )
    mock_post = mocker.patch(
        "app.notify_client.NotifyAdminAPIClient.post", return_value={"png": base64.b64encode(b"\x89PNG").decode()}
    )

    assert client.get_png_for_invalid_pdf_page("service-id", b"%PDF", "2") == (
        b"\x89PNG",
        200,
        {"Content-Type": "image/png"},
    )
    assert mock_extract.call_args.args[1] == 1  # zero-indexed
    mock_post.assert_called_once_with(
        url="/service/service-id/letter-upload/overlay.png",
        data={"file": base64.b64encode(b"page 2").decode(), "page_number": 2},
    )
