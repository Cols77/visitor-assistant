from __future__ import annotations

from tourassist.app.security.auth import create_tenant, validate_api_key


def test_api_key_validation():
    data = create_tenant("tenant-sec")
    assert validate_api_key("tenant-sec", data["api_key"]) is True
    assert validate_api_key("tenant-sec", "bad-key") is False
    other = create_tenant("tenant-other")
    assert validate_api_key("tenant-sec", other["api_key"]) is False
