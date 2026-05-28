from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import mythic_container
import nano_bofs_mythic


mythic_container.mythic_service.start_and_run_forever()
