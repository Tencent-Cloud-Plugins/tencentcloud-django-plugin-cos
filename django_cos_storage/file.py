from io import BytesIO
from shutil import copyfileobj
from tempfile import SpooledTemporaryFile

from django.core.files.base import File


class TencentCOSFile(File):
    def __init__(self, name, storage):
        self.name = name
        self._storage = storage
        self._file = None

    @property
    def file(self):
        if self._file is None:
            self._file = SpooledTemporaryFile()
            response = self._storage.client.get_object(
                Bucket=self._storage.bucket,
                Key=self.name,
            )
            raw_stream = response["Body"].get_raw_stream()
            with BytesIO(raw_stream.data) as file_content:
                copyfileobj(file_content, self._file)
            self._file.seek(0)
        return self._file

    @file.setter
    def file(self, value):
        self._file = value
