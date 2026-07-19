from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Iterator

from src.ingestion.schema import NormalizedEvent

FIELD_MAP = {
    "SubjectUserName": "subject_user_name",
    "SubjectUserSid": "subject_user_sid",
    "SubjectDomainName": "subject_domain_name",
    "SubjectLogonId": "subject_logon_id",
    "TargetUserName": "target_user_name",
    "TargetUserSid": "target_user_sid",
    "TargetDomainName": "target_domain_name",
    "LogonType": "logon_type",
    "TicketEncryptionType": "ticket_encryption_type",
    "TicketOptions": "ticket_options",
    "FailureReason": "failure_reason",
    "Status": "status",
    "SubStatus": "sub_status",
    "AuthenticationPackageName": "authentication_package",
    "IpAddress": "ip_address",
    "IpPort": "ip_port",
    "WorkstationName": "workstation_name",
    "ObjectName": "object_name",
    "ObjectType": "object_type",
    "ObjectServer": "object_server",
    "OperationType": "operation_type",
    "AccessMask": "access_mask",
    "Properties": "properties",
    "PrivilegeList": "privilege_list",
}


def _extract_timestamp_raw(obj):
    return obj.get("EventTime") or obj.get("@timestamp")


def parse_mordor_line(obj, source_dataset, source_file):
    if "EventID" not in obj:
        return None

    kwargs = {
        "event_id": obj["EventID"],
        "timestamp": _extract_timestamp_raw(obj),
        "computer": obj.get("Hostname", obj.get("host", "UNKNOWN")),
        "hostname_raw": obj.get("Hostname"),
        "source_dataset": source_dataset,
        "source_file": source_file,
        "source_format": "mordor_jsonl",
        "record_id": str(obj.get("RecordNumber")) if obj.get("RecordNumber") is not None else None,
        "raw": obj,
    }
    for mordor_key, target_key in FIELD_MAP.items():
        if mordor_key in obj:
            kwargs[target_key] = obj[mordor_key]

    try:
        return NormalizedEvent(**kwargs)
    except Exception as exc:
        print(f"[WARN] Ligne ignoree ({source_file}): {exc}", file=sys.stderr)
        return None


def parse_mordor_file(filepath, source_dataset):
    path = Path(filepath)
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            event = parse_mordor_line(obj, source_dataset, path.name)
            if event is not None:
                yield event


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python -m src.ingestion.mordor_parser <input.json> <source_dataset_name>")
        sys.exit(1)

    events = list(parse_mordor_file(sys.argv[1], sys.argv[2]))
    print(f"{len(events)} evenements normalises depuis {sys.argv[1]}")
    if events:
        print("Exemple:", events[0].model_dump_json(indent=2)[:800])
