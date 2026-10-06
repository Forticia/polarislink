"""
Forticia PolarisLink™ — Official Institutional Client Library
Zero-dependency Python client for Forticia Research, 8D Options Surfaces, and Quantitative Market Data Vault.
"""

from .client import (
    ForticiaClient,
    PolarisLinkClient,
    PolarisLink,
    enforce_institutional_guardrails,
)

__version__ = "2.6.1"

__all__ = [
    "ForticiaClient",
    "PolarisLinkClient",
    "PolarisLink",
    "enforce_institutional_guardrails",
    "__version__",
]
