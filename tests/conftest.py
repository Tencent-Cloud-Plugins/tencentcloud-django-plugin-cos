import pytest
from django_cos_storage.storage import TencentCOSStorage


@pytest.fixture
def storage():
    return TencentCOSStorage(
        bucket="test-bucket",
        config={
            "Region": "region",
            "SecretId": "********",
            "SecretKey": "********",
        },
    )
