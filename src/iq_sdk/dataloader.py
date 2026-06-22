"""I/Q data dataloading."""

import glob
import os
import re
from typing import Generic

import numpy as np
import yaml
from abstract_dataloader import abstract
from abstract_dataloader.ext.types import TArray, dataclass
from jaxtyping import Complex64, Float64


@dataclass
class IQData(Generic[TArray]):
    """A batch of I/Q data samples.

    Attributes:
        iq: Complex I/Q samples.
        timestamps: Unix epoch timestamps (seconds) for the start of each
            interval.
    """

    iq: Complex64[TArray, "batch interval"]
    timestamps: Float64[TArray, "batch"]


@dataclass
class ReceiverMetadata:
    """Metadata for a `Receiver` sensor.

    Attributes:
        timestamps: Unix epoch timestamp (seconds) for the start of each
            interval, interpolated from per-capture timestamps.
        chunks: Chunk file paths, sorted by numeric index.
        samples_per_chunk: Number of I/Q samples in each chunk.
        total_samples: Total number of I/Q samples in the recording.
        interval: Number of I/Q samples per `IQData` item.
    """

    timestamps: Float64[np.ndarray, " n"]
    chunks: list[str]
    samples_per_chunk: int
    total_samples: int
    interval: int


class Receiver(abstract.Sensor[IQData, ReceiverMetadata]):
    """Sensor for reading I/Q data from a receiver directory.

    Args:
        path: Path to the receiver directory (e.g. `"data/recording/rx0"`).
        interval: Number of I/Q samples returned per `IQData` sample.
            If `None`, defaults to `samples_per_capture` from `meta.yaml`.
        name: Sensor name passed to the base class.
    """

    @staticmethod
    def _chunk_index(path: str) -> int:
        # Numeric index of an `iq{N}.c8` chunk, from its basename. Keying on the
        # filename (not the full path) is essential: a digit elsewhere in the
        # path -- e.g. `.../data0/run-6-18-26/rx1/iq3.c8` -- must not affect the
        # order. The `\.c8` anchor stops a stray index digit being mismatched.
        match = re.fullmatch(r"iq(\d+)\.c8", os.path.basename(path))
        if match is None:
            raise ValueError(f"Chunk file is not named iq<N>.c8: {path}")
        return int(match.group(1))

    def __init__(
        self,
        path: str,
        interval: int | None = None,
        name: str = "rx",
    ) -> None:
        with open(f"{path}/meta.yaml") as f:
            meta = yaml.safe_load(f)

        samples_per_capture: int = meta["samples_per_capture"]
        captures_per_chunk: int = meta["captures_per_chunk"]
        total_captures: int = meta["captures"]

        samples_per_chunk = captures_per_chunk * samples_per_capture
        total_samples = total_captures * samples_per_capture
        interval = samples_per_capture if interval is None else interval

        # Load per-capture timestamps and build interpolation arrays.
        capture_timestamps: Float64[np.ndarray, " captures"] = np.fromfile(
            f"{path}/ts.f8", dtype="<f8"
        )
        capture_starts = (
            np.arange(total_captures, dtype=np.float64) * samples_per_capture
        )

        # One timestamp per interval, interpolated from capture timestamps.
        n = total_samples // interval
        interval_starts = np.arange(n, dtype=np.float64) * interval
        timestamps: Float64[np.ndarray, " n"] = np.interp(
            interval_starts, capture_starts, capture_timestamps
        )

        # Sort chunks by their numeric index, rejecting malformed names and
        # duplicate indices (which would silently corrupt the read order).
        indexed = sorted(
            (self._chunk_index(p), p) for p in glob.glob(f"{path}/iq*.c8")
        )
        indices = [i for i, _ in indexed]
        duplicates = sorted({i for i in indices if indices.count(i) > 1})
        if duplicates:
            raise ValueError(
                f"Duplicate chunk indices {duplicates} among iq*.c8 in {path}"
            )
        chunks = [p for _, p in indexed]

        super().__init__(
            metadata=ReceiverMetadata(
                timestamps=timestamps,
                chunks=chunks,
                samples_per_chunk=samples_per_chunk,
                total_samples=total_samples,
                interval=interval,
            ),
            name=name,
        )

    def __getitem__(self, index: int | np.integer) -> IQData[np.ndarray]:
        """Return one interval of I/Q samples.

        Args:
            index: Sample index (0-based).

        Returns:
            `IQData` with `iq` of dtype `complex64` and `timestamps` in
                Unix epoch seconds.
        """
        idx = int(index)
        meta = self.metadata
        start = idx * meta.interval

        iq = np.empty(meta.interval, dtype=np.complex64)
        written = 0
        pos = start

        while written < meta.interval:
            chunk_idx = pos // meta.samples_per_chunk
            offset = pos % meta.samples_per_chunk

            chunk_samples = min(
                meta.samples_per_chunk,
                meta.total_samples - chunk_idx * meta.samples_per_chunk,
            )
            mmap = np.memmap(
                meta.chunks[chunk_idx],
                dtype=np.complex64,
                mode="r",
                shape=(chunk_samples,),
            )
            to_read = min(meta.interval - written, chunk_samples - offset)
            iq[written : written + to_read] = mmap[offset : offset + to_read]
            written += to_read
            pos += to_read

        timestamps = np.array([meta.timestamps[idx]], dtype=np.float64)
        return IQData(iq=iq[np.newaxis], timestamps=timestamps)
