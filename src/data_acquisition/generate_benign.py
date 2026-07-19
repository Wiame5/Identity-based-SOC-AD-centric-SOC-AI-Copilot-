from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timedelta

N_USERS = 40
N_COMPUTERS = 15
DOMAIN = "INTERNAL"
START_DATE = datetime(2022, 3, 1)
N_DAYS = 14

USERS = [f"user{i:03d}" for i in range(1, N_USERS + 1)]
COMPUTERS = [f"WS{i:03d}.internal.local" for i in range(1, N_COMPUTERS + 1)]
DC = "DC01.internal.local"

USER_HOME_COMPUTERS = {
    u: random.sample(COMPUTERS, k=random.choice([1, 1, 1, 2])) for u in USERS
}

BENIGN_EVENT_TEMPLATES = [
    (4624, 50, "logon_success"),
    (4634, 45, "logoff"),
    (4768, 20, "kerberos_tgt_request"),
    (4769, 25, "kerberos_service_ticket"),
    (4672, 5, "special_privileges_assigned"),
]


def _business_hour_timestamp(day_offset):
    hour = int(random.gauss(mu=random.choice([9, 14]), sigma=2.5))
    hour = max(7, min(19, hour))
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    base = START_DATE + timedelta(days=day_offset)
    return base.replace(hour=hour, minute=minute, second=second)


def generate_benign_events(n_events):
    events = []
    for i in range(n_events):
        user = random.choice(USERS)
        computer = random.choice(USER_HOME_COMPUTERS[user])
        day_offset = random.randint(0, N_DAYS - 1)
        timestamp = _business_hour_timestamp(day_offset)

        event_id, _, _ = random.choices(
            BENIGN_EVENT_TEMPLATES,
            weights=[w for _, w, _ in BENIGN_EVENT_TEMPLATES],
        )[0]

        record = {
            "event_id": event_id,
            "timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%S"),
            "computer": computer,
            "subject_user_name": user,
            "subject_domain_name": DOMAIN,
            "record_id": str(1000000 + i),
            "source_dataset": "benign_synthetic",
            "source_file": "benign_synthetic.json",
            "source_format": "synthetic",
            "label": "benign",
            "mitre_tactic": None,
            "mitre_technique": None,
        }

        if event_id in (4768, 4769):
            record["ticket_encryption_type"] = "0x12"
            record["target_domain_name"] = DOMAIN
        if event_id == 4624:
            record["logon_type"] = random.choice([2, 2, 2, 10])
        if event_id == 4672:
            record["subject_logon_id"] = f"0x{random.randint(10000,99999):x}"

        events.append(record)

    events.sort(key=lambda e: e["timestamp"])
    return events


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output_path")
    parser.add_argument("--n-events", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    events = generate_benign_events(args.n_events)

    with open(args.output_path, "w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e) + "\n")

    print(f"{len(events)} evenements benins synthetiques generes -> {args.output_path}")
    print(f"Utilisateurs distincts : {len(USERS)} | Machines distinctes : {len(COMPUTERS)}")
    print(f"Periode simulee : {N_DAYS} jours a partir de {START_DATE.date()}")
