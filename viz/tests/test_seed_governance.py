import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import seed_governance


def test_load_sql_files_found():
    paths = seed_governance.sql_file_paths()
    names = {p.name for p in paths}
    assert "dim_branch_patch.sql" in names
    assert "external_channel_map.sql" in names
