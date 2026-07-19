import re
from pathlib import Path

path = Path("src/features/feature_engineering.py")
content = path.read_text(encoding="utf-8")

marker = "def build_label_to_tactic_map(df_train):"

new_block = '''MORDOR_MANUAL_MITRE_MAP = {
    "dcsync_convenant": ("TA0006", "T1003.006"),
    "dcsync_empire": ("TA0006", "T1003.006"),
    "mimikatz": ("TA0006", "T1003.001"),
    "kerberos_createnetonly": ("TA0008", "T1550.003"),
    "ntds_dump_ninjacopy": ("TA0006", "T1003.003"),
    "ntds_dump_ntdsutil": ("TA0006", "T1003.003"),
    "ntds_dump_shadowcopy": ("TA0006", "T1003.003"),
    # benign volontairement absent : pas de tactique MITRE, reste None
}


def build_label_to_tactic_map(df_train):'''

if marker not in content:
    print("[ERREUR] Marqueur introuvable")
elif "MORDOR_MANUAL_MITRE_MAP" in content:
    print("[INFO] Deja applique")
else:
    content = content.replace(marker, new_block)
    path.write_text(content, encoding="utf-8")
    print("[OK] Mapping manuel Mordor ajoute")
