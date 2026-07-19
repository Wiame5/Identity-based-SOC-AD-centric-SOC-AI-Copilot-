import sys
from Evtx.Evtx import Evtx

def inspect_file(filepath, max_events=3):
    print(f"=== Inspection de {filepath} ===\n")
    with Evtx(filepath) as log:
        for i, record in enumerate(log.records()):
            if i >= max_events:
                break
            print(f"--- Event {i} ---")
            print(record.xml())
            print()

if __name__ == '__main__':
    inspect_file(sys.argv[1], max_events=int(sys.argv[2]) if len(sys.argv) > 2 else 3)
