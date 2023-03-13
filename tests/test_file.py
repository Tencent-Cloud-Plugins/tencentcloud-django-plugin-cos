from io import BytesIO
from tempfile import SpooledTemporaryFile
from unittest.mock import MagicMock

import pytest
from qcloud_cos.cos_client import CosS3Client
from qcloud_cos.streambody import StreamBody
from requests.models import Response
from urllib3.response import HTTPResponse
from django_cos_storage.file import TencentCOSFile


def test_get_file(monkeypatch: pytest.MonkeyPatch, storage):
    requests_response = Response()
    requests_response.raw = HTTPResponse(
        body=b"test file content",
    )
    requests_response.headers = {
        "Content-Length": "17",
    }
    mock = MagicMock(return_value={"Body": StreamBody(requests_response)})
    monkeypatch.setattr(CosS3Client, "get_object", mock)
    tencentcos_file = TencentCOSFile(name="test-file", storage=storage)
    assert isinstance(tencentcos_file.file, SpooledTemporaryFile)
    assert tencentcos_file.file.read() == b"test file content"
    mock.assert_called_once()


def test_set_file(storage):
    tencentcos_file = TencentCOSFile(name="test-file", storage=storage)
    tencentcos_file.file = BytesIO(b"test file content")
    assert isinstance(tencentcos_file.file, BytesIO)
    assert tencentcos_file.file.read() == b"test file content"
