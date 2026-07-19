import re
from pathlib import Path

path = Path("src/features/feature_engineering.py")
content = path.read_text(encoding="utf-8")

old_block = '''        n_events = g["event_id"].rolling(window).count()
        n_distinct_eventid = g["event_id"].rolling(window).apply(
            lambda x: pd.Series(x).nunique(), raw=False
        )
        n_distinct_computer = g["computer"].rolling(window).apply(
            lambda x: pd.Series(x).nunique(), raw=False
        ) if "computer" in g.columns else pd.Series(0, index=g.index)'''

new_block = '''        n_events = g["event_id"].rolling(window).count()

        eventid_codes = pd.Series(
            pd.factorize(g["event_id"])[0], index=g.index
        ).astype(float)
        n_distinct_eventid = eventid_codes.rolling(window).apply(
            lambda x: pd.Series(x).nunique(), raw=True
        )

        if "computer" in g.columns:
            computer_codes = pd.Series(
                pd.factorize(g["computer"])[0], index=g.index
            ).astype(float)
            n_distinct_computer = computer_codes.rolling(window).apply(
                lambda x: pd.Series(x).nunique(), raw=True
            )
        else:
            n_distinct_computer = pd.Series(0, index=g.index)'''

if old_block not in content:
    print("[ERREUR] Bloc introuvable - verifie le fichier manuellement")
else:
    content = content.replace(old_block, new_block)
    path.write_text(content, encoding="utf-8")
    print("[OK] Fix rolling applique dans feature_engineering.py")
