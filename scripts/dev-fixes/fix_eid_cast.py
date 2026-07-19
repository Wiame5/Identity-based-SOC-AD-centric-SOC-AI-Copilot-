import re
from pathlib import Path

path = Path("src/copilot/model_inference.py")
content = path.read_text(encoding="utf-8")

old_eid = '''        eid = event.get("event_id")
        row["event_id_freq"] = self.freq_map.get(eid, 0.0)
        for top_eid in self.top_event_ids:
            row[f"eid_{top_eid}"] = int(eid == top_eid)
        row["eid_other"] = int(eid not in self.top_event_ids)'''

new_eid = '''        eid = event.get("event_id")
        eid = int(eid) if eid is not None else None
        row["event_id_freq"] = self.freq_map.get(eid, 0.0)
        for top_eid in self.top_event_ids:
            row[f"eid_{top_eid}"] = int(eid == top_eid)
        row["eid_other"] = int(eid not in self.top_event_ids)'''

if old_eid not in content:
    print("[ERREUR] Bloc eid introuvable")
else:
    content = content.replace(old_eid, new_eid)
    path.write_text(content, encoding="utf-8")
    print("[OK] Cast event_id en int natif applique")
