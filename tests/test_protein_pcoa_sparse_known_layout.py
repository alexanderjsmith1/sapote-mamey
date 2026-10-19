"""Validate the actual >400-row sparse solver with independent known distances."""
from pathlib import Path
import os,importlib.util
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[1]
source=Path(os.environ.get('LANE06_ORDINATE_SOURCE',ROOT/'tools/protein_pcoa_ordinate.py'))
spec=importlib.util.spec_from_file_location('sparse_known_ordinate',source);ppo=importlib.util.module_from_spec(spec);spec.loader.exec_module(ppo)

def test_sparse_pcoa_recovers_known_line_distances():
    pytest.importorskip('scipy')
    positions=np.linspace(0,1,401,dtype=np.float64)
    expected=np.abs(positions[:,None]-positions[None,:])
    matrix=expected.astype(np.float32)
    coords,pct=ppo.classical_pcoa(matrix.copy(),k=3)
    recovered=np.linalg.norm(coords[:,None,:]-coords[None,:,:],axis=2)
    assert coords.shape==(401,3) and np.isfinite(coords).all()
    assert np.max(np.abs(recovered-expected))<1e-4
    assert abs(pct[0]-100)<1e-3
