import importlib.util
from pathlib import Path

import numpy as np


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "maintenance" / "run_mmwave_preselection_clutter_ab_20260830.py"


def load_module():
    spec = importlib.util.spec_from_file_location("clutter_ab", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_complex_mean_subtract_removes_slow_time_complex_mean():
    module = load_module()
    cube = np.full((5, 2, 3), 3 + 4j, dtype=np.complex64)
    cube[:, 1, 2] += np.arange(5, dtype=np.float32)
    result = module.complex_mean_subtract(cube)
    assert np.allclose(np.mean(result, axis=0), 0.0)
    assert result.shape == cube.shape
