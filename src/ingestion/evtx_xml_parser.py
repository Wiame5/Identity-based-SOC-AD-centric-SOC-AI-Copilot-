from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Iterator

import yaml
from Evtx.Evtx import Evtx
from lxml import etree

from src.ingestion.schema import NormalizedEvent

NS = {"e": "http://schemas.microsoft.com/win/2004/08/events/event"}

DATA_NAME_MAP = {
    "SubjectUserName": "subject_user_name",
    "SubjectUserSid": "subject_user_sid",
    "SubjectDomainName": "subject_domain_name",
    "SubjectLogonId": "subject_logon_id",
    "TargetUserName": "target_user_name",
    "TargetUserSid": "target_user_sid",
    "TargetSid": "target_user_sid",
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


def _parse_single_xml(xml_str, source_dataset, source_file, label, tactic, technique):
    try:
        root = etree.fromstring(xml_str.encode("utf-8"))
    except etree.XMLSyntaxError:
        return None

    system = root.find("e:System", NS)
    if system is None:
        return None

    event_id_el = system.find("e:EventID", NS)
    if event_id_el is None or event_id_el.text is None:
        return None
    event_id = int(event_id_el.text)

    time_el = system.find("e:TimeCreated", NS)
    timestamp_raw = time_el.get("SystemTime") if time_el is not None else None
    if timestamp_raw is None:
        return None

    ts_normalized = timestamp_raw.replace(" ", "T")
    try:
        dt = datetime.fromisoformat(ts_normalized)
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        timestamp_clean = dt.isoformat()
    except ValueError:
        timestamp_clean = timestamp_raw.split(".")[0].split("+")[0].replace(" ", "T")

    computer_el = system.find("e:Computer", NS)
    computer = computer_el.text if computer_el is not None else "UNKNOWN"

    record_id_el = system.find("e:EventRecordID", NS)
    record_id = record_id_el.text if record_id_el is not None else None

    kwargs = {
        "event_id": event_id,
        "timestamp": timestamp_clean,
        "computer": computer,
        "hostname_raw": computer,
        "source_dataset": source_dataset,
        "source_file": source_file,
        "source_format": "evtx_xml",
        "record_id": record_id,
        "label": label,
        "mitre_tactic": tactic,
        "mitre_technique": technique,
        "raw": {"xml": xml_str},
    }

    event_data = root.find("e:EventData", NS)
    if event_data is not None:
        for data_el in event_data.findall("e:Data", NS):
            name = data_el.get("Name")
            value = data_el.text
            if name in DATA_NAME_MAP and value not in (None, "-", "%%1793"):
                target_field = DATA_NAME_MAP[name]
                if kwargs.get(target_field) is None:
                    kwargs[target_field] = value

    try:
        return NormalizedEvent(**kwargs)
    except Exception as exc:
        print(f"[WARN] Evenement ignore ({source_file}): {exc}", file=sys.stderr)
        return None


def parse_evtx_file(filepath, source_dataset, label, tactic, technique):
    path = Path(filepath)
    with Evtx(str(path)) as log:
        for record in log.records():
            event = _parse_single_xml(
                record.xml(), source_dataset, path.name, label, tactic, technique
            )
            if event is not None:
                yield event


def parse_all_from_manifest(manifest_path, evtx_root):
    with open(manifest_path, encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    all_events = []
    for category, entries in manifest.items():
        category_dir = Path(evtx_root) / category
        for entry in entries:
            filepath = category_dir / entry["file"]
            if not filepath.exists():
                print(f"[WARN] Fichier manquant, ignore: {filepath}", file=sys.stderr)
                continue
            events = list(parse_evtx_file(
                str(filepath),
                source_dataset=entry["label"],
                label=entry["label"],
                tactic=entry["tactic"],
                technique=entry["technique"],
            ))
            print(f"{entry['file']}: {len(events)} evenements ({entry['label']})")
            all_events.extend(events)

    return all_events


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m src.ingestion.evtx_xml_parser <manifest.yaml> [evtx_root]")
        sys.exit(1)

    manifest_path = sys.argv[1]
    evtx_root = sys.argv[2] if len(sys.argv) > 2 else "data/raw/evtx_selected"

    events = parse_all_from_manifest(manifest_path, evtx_root)
    total_files = len(list(Path(evtx_root).rglob("*.evtx")))
    print(f"\nTOTAL: {len(events)} evenements normalises depuis {total_files} fichiers")
