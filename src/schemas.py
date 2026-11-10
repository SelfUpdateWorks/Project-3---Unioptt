"""
schemas.py — The data shapes the agent produces.

Field names and allowed values mirror the VerificationRecord used in the
Unioptt backend, so the agent's output can later be loaded into Unioptt
without conversion.
"""
from typing import Literal, Optional

from pydantic import BaseModel

# The four allowed statuses (same words as in Unioptt)
VerificationStatus = Literal["Verified", "Inferred", "Needs Review", "Unknown"]

# Where a fact came from
VerificationSource = Literal["official", "inferred", "country_default", "unknown"]

# How likely the fact is correct
ConfidenceLevel = Literal["high", "medium", "low", "none"]


class VerificationRecord(BaseModel):
    """Provenance for one fact or one requirement section."""

    status: VerificationStatus
    source: VerificationSource
    source_url: Optional[str] = None
    last_verified: Optional[str] = None  # date as YYYY-MM-DD
    confidence: ConfidenceLevel
    notes: Optional[str] = None  # the exact quote from the source goes here

    model_config = {"frozen": True}  # cannot be changed after creation