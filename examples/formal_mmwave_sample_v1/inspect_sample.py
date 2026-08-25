"""Print the structure of the public formal mmWave sample."""
from pathlib import Path
import json
import numpy as np

root = Path(__file__).parent
print(json.loads((root / "metadata_sanitized.json").read_text(encoding="utf-8")))
for path in sorted(root.glob("mmwave_part_*.npz")):
    print(path.name)
    with np.load(path, allow_pickle=False) as z:
        for name in z.files:
            x = z[name]
            print(" ", name, x.dtype, x.shape, np.iscomplexobj(x))
