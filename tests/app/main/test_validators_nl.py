import json
from io import BytesIO
from unittest.mock import Mock

import pytest
from requests import Response
from werkzeug.datastructures import FileStorage
from wtforms.validators import StopValidation

from app.extensions import antivirus_client
from app.main.overrides_nl.validators import FileIsVirusFree


def _antivirus_response(ok):
    response = Response()
    response.status_code = 200
    response._content = json.dumps({"ok": ok}).encode()
    return response


@pytest.mark.parametrize("virus_free", [True, False])
def test_file_is_virus_free_sends_the_uploaded_file_to_antivirus(notify_admin, mocker, virus_free):
    # only the network call is mocked, so requests still has to encode the upload
    send = mocker.patch.object(antivirus_client.requests_session, "send", return_value=_antivirus_response(virus_free))
    field = Mock(data=FileStorage(BytesIO(b"%PDF-1.7 a letter"), filename="letter.pdf", name="file"))

    if virus_free:
        FileIsVirusFree()(None, field)
    else:
        with pytest.raises(StopValidation, match="Dit bestand bevat een virus"):
            FileIsVirusFree()(None, field)

    scan_request = send.call_args.args[0]
    assert scan_request.url == f"{notify_admin.config['ANTIVIRUS_API_HOST']}/scan"
    assert b"%PDF-1.7 a letter" in scan_request.body
    assert field.data.read() == b"%PDF-1.7 a letter"
