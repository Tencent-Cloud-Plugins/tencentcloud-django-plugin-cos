import io
from datetime import datetime, timezone
from unittest.mock import MagicMock
from requests.models import Response
from urllib3.response import HTTPResponse
from tempfile import SpooledTemporaryFile

import pytest
from django.core.exceptions import ImproperlyConfigured, SuspiciousFileOperation
from django.core.files.base import File
from django.core.files.storage import Storage
from qcloud_cos.cos_client import CosConfig, CosS3Client
from qcloud_cos.cos_exception import CosServiceError
from qcloud_cos.streambody import StreamBody

from django_cos_storage.storage import TencentCOSStorage


class TestTencentCOSStorage:
    def test_setting_without_bucket(self):
        with pytest.raises(ImproperlyConfigured):
            TencentCOSStorage()

    def test_setting_with_bucket(self, settings):
        settings.TENCENTCOS_STORAGE = {
            "BUCKET": "test-bucket",
            "CONFIG": {
                "Region": "region",
                "SecretId": "********",
                "SecretKey": "********",
            },
        }
        storage = TencentCOSStorage()
        assert storage.bucket == "test-bucket"

    def test_setting_miss_required_config_kwargs(self, settings):
        settings.TENCENTCOS_STORAGE = {
            "BUCKET": "test-bucket",
            "CONFIG": {
                "Region": "region",
            },
        }
        with pytest.raises(ImproperlyConfigured):
            TencentCOSStorage()

    def test_minimal_proper_setting(self, settings):
        settings.TENCENTCOS_STORAGE = {
            "BUCKET": "test-bucket",
            "CONFIG": {
                "Region": "region",
                "SecretId": "********",
                "SecretKey": "********",
            },
        }
        storage = TencentCOSStorage()
        assert storage.bucket == "test-bucket"
        assert storage.root_path == "/"
        assert storage.upload_max_buffer_size is None
        assert storage.upload_part_size is None
        assert storage.upload_max_thread is None

        config = storage.client.get_conf()
        assert config._region == "region"
        assert config._secret_id == "********"
        assert config._secret_key == "********"

    def test_full_proper_setting(self, settings):
        settings.TENCENTCOS_STORAGE = {
            "BUCKET": "test-bucket",
            "UPLOAD_MAX_BUFFER_SIZE": 200,
            "UPLOAD_PART_SIZE": 5,
            "UPLOAD_MAX_THREAD": 10,
            "CONFIG": {
                "Region": "region",
                "SecretId": "********",
                "SecretKey": "********",
            },
        }
        storage = TencentCOSStorage()
        assert storage.bucket == "test-bucket"
        assert storage.root_path == "/"
        assert storage.upload_max_buffer_size == 200
        assert storage.upload_part_size == 5
        assert storage.upload_max_thread == 10

    def test_normalize_root_path(self):
        storage = TencentCOSStorage(
            bucket="test-bucket",
            root_path="/namespace",
            config={
                "Region": "region",
                "SecretId": "********",
                "SecretKey": "********",
            },
        )
        assert storage.root_path == "/namespace/"

    def test_delete(self, monkeypatch, storage):
        mm = MagicMock(return_value=None)
        monkeypatch.setattr(CosS3Client, "delete_object", mm)
        assert storage.delete("test-file") is None

    def test_exists(self, monkeypatch, storage):
        mm = MagicMock(return_value={"foo": "bar"})
        monkeypatch.setattr(CosS3Client, "head_object", mm)
        assert storage.exists("test-file") is True

    def test_does_not_exists(self, monkeypatch, storage):
        mm = MagicMock(
            side_effect=CosServiceError(
                method="", message={"code": "NoSuchResource"}, status_code=404
            ),
        )
        monkeypatch.setattr(CosS3Client, "head_object", mm)
        assert storage.exists("nonexistence-file") is False

    def test_exists_raise_exception(self, monkeypatch, storage):
        mm = MagicMock(
            side_effect=CosServiceError(
                method="", message={"code": "Denied"}, status_code=403
            )
        )
        monkeypatch.setattr(CosS3Client, "head_object", mm)
        with pytest.raises(CosServiceError):
            storage.exists("test-file")

    def test_listdir_not_truncated(self, monkeypatch, storage):
        mm = MagicMock(
            return_value={
                "Contents": [
                    {"Key": "dir1/"},
                    {"Key": "dir2/"},
                    {"Key": "file1"},
                    {"Key": "file2"},
                ],
                "IsTruncated": "false",
            },
        )
        monkeypatch.setattr(CosS3Client, "list_objects", mm)
        dirs, files = storage.listdir("")
        assert dirs == ["dir1/", "dir2/"]
        assert files == ["file1", "file2"]

    def test_listdir_truncated(self, monkeypatch, storage):
        mm = MagicMock(
            side_effect=[
                {
                    "Contents": [
                        {"Key": "dir1/"},
                        {"Key": "file1"},
                    ],
                    "IsTruncated": "true",
                    "NextMarker": 2,
                },
                {
                    "Contents": [
                        {"Key": "dir2/"},
                        {"Key": "file2"},
                    ],
                    "IsTruncated": "false",
                },
            ],
        )
        monkeypatch.setattr(CosS3Client, "list_objects", mm)
        dirs, files = storage.listdir("")
        assert dirs == ["dir1/", "dir2/"]
        assert files == ["file1", "file2"]
        assert mm.call_count == 2

    def test_size(self, monkeypatch, storage):
        mm = MagicMock(return_value={"Content-Length": 10})
        monkeypatch.setattr(CosS3Client, "head_object", mm)
        assert storage.size("test-file") == 10

    def test_get_modified_time_use_tz(self, monkeypatch, settings, storage):
        mm = MagicMock(return_value={"Last-Modified": "Sun, 22 Aug 2021 04:18:16 GMT"})
        monkeypatch.setattr(CosS3Client, "head_object", mm)
        settings.USE_TZ = True
        assert storage.get_modified_time("test-file") == datetime(
            2021, 8, 22, 4, 18, 16, tzinfo=timezone.utc
        )

    def test_get_modified_time_does_not_use_tz(self, monkeypatch, settings, storage):
        mm = MagicMock(return_value={"Last-Modified": "Sun, 22 Aug 2021 04:18:16 GMT"})
        monkeypatch.setattr(CosS3Client, "head_object", mm)
        settings.USE_TZ = False
        timestamp = datetime(2021, 8, 22, 4, 18, 16, tzinfo=timezone.utc).timestamp()
        assert storage.get_modified_time("test-file") == datetime.fromtimestamp(
            timestamp
        )

    def test_get_accessed_time_not_implemented(self, storage):
        with pytest.raises(NotImplementedError):
            storage.get_accessed_time("test-file")

    def test_get_created_time_not_implemented(self, storage):
        with pytest.raises(NotImplementedError):
            storage.get_accessed_time("test-file")

    def test__open(self, monkeypatch, storage):
        requests_response = Response()
        requests_response.raw = HTTPResponse(
            body=b"test file content",
        )
        requests_response.headers = {
            "Content-Length": "17",
        }
        mm = MagicMock(return_value={"Body": StreamBody(requests_response)})
        monkeypatch.setattr(CosS3Client, "get_object", mm)
        get_file = storage._open("file2")
        assert isinstance(get_file, SpooledTemporaryFile)
        assert get_file.read() == b"test file content"
        mm.assert_called_once()
        # assert isinstance(obj, File)

    def test__save_with_default_upload_kwargs(self, monkeypatch, storage):
        content = File(io.BytesIO(b"bar"), "foo")
        mm = MagicMock(
            return_value=None,
        )
        monkeypatch.setattr(CosS3Client, "upload_file_from_buffer", mm)
        storage._save("file", content)
        mm.assert_called_once_with("test-bucket", "/file", content)

    def test__save_with_custom_upload_kwargs(self, monkeypatch, settings):
        settings.TENCENTCOS_STORAGE = {
            "BUCKET": "test-bucket",
            "UPLOAD_MAX_BUFFER_SIZE": 200,
            "UPLOAD_PART_SIZE": 5,
            "UPLOAD_MAX_THREAD": 10,
            "CONFIG": {
                "Region": "region",
                "SecretId": "********",
                "SecretKey": "********",
            },
        }
        storage = TencentCOSStorage()
        mm = MagicMock(return_value=None)
        monkeypatch.setattr(CosS3Client, "upload_file_from_buffer", mm)
        content = File(io.BytesIO(b"bar"), "foo")
        storage._save("file", content)
        mm.assert_called_once_with(
            "test-bucket", "/file", content, MaxBufferSize=200, PartSize=5, MAXThread=10
        )

    def test_url(self, monkeypatch, storage):
        mm = MagicMock()
        monkeypatch.setattr(CosConfig, "uri", mm)
        storage.url("test")
        mm.assert_called()
        mm.assert_called_with(bucket=storage.bucket, path="/test")

    def test__full_path(self, storage):
        assert storage._full_path("/") == "/"
        assert storage._full_path("") == "/"
        assert storage._full_path(".") == "/"
        assert storage._full_path("..") == "/"
        assert storage._full_path("../..") == "/"

        storage.root_path = "/namespace"
        assert storage._full_path("/") == "/namespace"
        assert storage._full_path("") == "/namespace"
        assert storage._full_path(".") == "/namespace"

        with pytest.raises(SuspiciousFileOperation):
            assert storage._full_path("..") == "/namespace"
        with pytest.raises(SuspiciousFileOperation):
            assert storage._full_path("../..") == "/namespace"

    def test_get_available_name(self, monkeypatch, storage):
        mm1 = MagicMock()
        mm2 = MagicMock()
        monkeypatch.setattr(TencentCOSStorage, "_full_path", mm1)
        monkeypatch.setattr(Storage, "get_available_name", mm2)
        storage.get_available_name("test")
        mm1.assert_called()
        mm2.assert_called()
