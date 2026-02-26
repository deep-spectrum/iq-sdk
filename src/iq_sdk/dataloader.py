"""I/Q data dataloading."""

import glob
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

        chunks = sorted(
            glob.glob(f"{path}/iq*.c8"),
            key=lambda p: int(re.findall(r"\d+", p)[0]),
        )

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
