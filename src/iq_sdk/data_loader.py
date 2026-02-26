import numpy as np
import numpy.typing as npt
from pathlib import Path
import yaml


def load_chunk(directory: str | Path, chunk_id: int) -> tuple[npt.NDArray[np.float64], npt.NDArray[np.complex64]]:
    if isinstance(directory, str):
        directory = Path(directory)
    with open(directory / "meta.yaml", "r") as f:
        meta = yaml.safe_load(f)

    captures_per_chunk = meta["captures_per_chunk"]
    samples_per_capture = meta["samples_per_capture"]
    first_capture = chunk_id * captures_per_chunk
    last_capture = (chunk_id + 1) * captures_per_chunk

    with open(directory / "ts.f8", "rb") as f:
        ts = np.fromfile(f, dtype='<f8')

    with open(directory / f"iq{chunk_id}.c8", "rb") as f:
        iq = np.fromfile(f, dtype="<c8", count=captures_per_chunk*samples_per_capture)

    iq = iq.reshape((captures_per_chunk, samples_per_capture))
    ts = ts[first_capture:last_capture]
    return ts, iq
