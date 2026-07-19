from __future__ import annotations

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator


class NormalizedEvent(BaseModel):
    event_id: int
    timestamp: datetime
    computer: str = Field(default="UNKNOWN")

    subject_user_name: Optional[str] = None
    subject_user_sid: Optional[str] = None
    subject_domain_name: Optional[str] = None
    subject_logon_id: Optional[str] = None

    target_user_name: Optional[str] = None
    target_user_sid: Optional[str] = None
    target_domain_name: Optional[str] = None

    logon_type: Optional[int] = None
    ticket_encryption_type: Optional[str] = None
    ticket_options: Optional[str] = None
    failure_reason: Optional[str] = None
    status: Optional[str] = None
    sub_status: Optional[str] = None
    authentication_package: Optional[str] = None

    ip_address: Optional[str] = None
    ip_port: Optional[str] = None
    workstation_name: Optional[str] = None

    object_name: Optional[str] = None
    object_type: Optional[str] = None
    object_server: Optional[str] = None
    operation_type: Optional[str] = None
    access_mask: Optional[str] = None
    properties: Optional[str] = None
    privilege_list: Optional[str] = None

    source_dataset: str
    source_file: str
    source_format: str
    hostname_raw: Optional[str] = None
    record_id: Optional[str] = None

    label: Optional[str] = None
    mitre_tactic: Optional[str] = None
    mitre_technique: Optional[str] = None

    raw: dict[str, Any] = Field(default_factory=dict)

    @field_validator("event_id", mode="before")
    @classmethod
    def _coerce_event_id(cls, v):
        return int(v)

    @field_validator("timestamp", mode="before")
    @classmethod
    def _coerce_timestamp(cls, v):
        if isinstance(v, datetime):
            return v
        if isinstance(v, str):
            for fmt in (
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S",
            ):
                try:
                    return datetime.strptime(v, fmt)
                except ValueError:
                    continue
        raise ValueError(f"Timestamp non reconnu: {v!r}")

    class Config:
        extra = "ignore"
