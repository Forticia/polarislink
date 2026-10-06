import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from polarislink import (
    PolarisLinkClient,
    ForticiaClient,
    enforce_institutional_guardrails,
    __version__,
)


def test_version():
    assert __version__ == "2.6.1"


def test_client_init_offline():
    client = PolarisLinkClient(api_key="demo_key", base_url="https://test.forticia.uk")
    assert client.api_key == "demo_key"
    assert client.base_url == "https://test.forticia.uk"
    assert client.timeout == 30


def test_client_alias():
    assert PolarisLinkClient is ForticiaClient


def test_institutional_guardrails():
    enforce_institutional_guardrails("ibkr")
    enforce_institutional_guardrails("cme")
    enforce_institutional_guardrails("opra")
    enforce_institutional_guardrails(None)

    with pytest.raises(RuntimeError) as exc_info:
        enforce_institutional_guardrails("yfinance")
    assert "Retail provider 'yfinance' is strictly prohibited" in str(exc_info.value)

    with pytest.raises(RuntimeError):
        enforce_institutional_guardrails("yahoo")

    with pytest.raises(RuntimeError):
        enforce_institutional_guardrails("polygon_free")
