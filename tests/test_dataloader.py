"""Unit tests for iq_sdk.dataloader."""

import os

import numpy as np
import pytest

from iq_sdk import IQData, Receiver, ReceiverMetadata

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_DATA_DIR = os.environ.get("IQ_TEST_DATA", "")


@pytest.fixture(scope="module")
def rx_path() -> str:
    """Path to the receiver directory under IQ_TEST_DATA."""
    if not _DATA_DIR:
        pytest.fail("IQ_TEST_DATA environment variable is not set.")
    return f"{_DATA_DIR}/rx0"


@pytest.fixture(scope="module")
def rx_default(rx_path: str) -> Receiver:
    """Receiver with the default interval (samples_per_capture)."""
    return Receiver(rx_path)


@pytest.fixture(scope="module")
def rx_small(rx_path: str) -> Receiver:
    """Receiver with a small custom interval (4096 samples)."""
    return Receiver(rx_path, interval=4096)


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


class TestReceiverMetadata:
    def test_type(self, rx_default: Receiver) -> None:
        assert isinstance(rx_default.metadata, ReceiverMetadata)

    def test_timestamps_dtype(self, rx_default: Receiver) -> None:
        assert rx_default.metadata.timestamps.dtype == np.float64

    def test_timestamps_length_matches_len(self, rx_default: Receiver) -> None:
        assert len(rx_default.metadata.timestamps) == len(rx_default)

    def test_chunks_sorted(self, rx_default: Receiver) -> None:
        """Chunk files must be in ascending numeric order."""
        import re

        indices = [
            int(re.findall(r"\d+", c)[0])
            for c in rx_default.metadata.chunks
        ]
        assert indices == sorted(indices)

    def test_chunks_nonempty(self, rx_default: Receiver) -> None:
        assert len(rx_default.metadata.chunks) > 0

    def test_interval_default(self, rx_default: Receiver) -> None:
        """Default interval equals samples_per_capture."""
        meta = rx_default.metadata
        expected = meta.total_samples // len(rx_default)
        assert meta.interval == expected

    def test_interval_custom(self, rx_small: Receiver) -> None:
        assert rx_small.metadata.interval == 4096


# ---------------------------------------------------------------------------
# Length
# ---------------------------------------------------------------------------


class TestLen:
    def test_default_interval_matches_total_captures(
        self, rx_default: Receiver
    ) -> None:
        """With interval=samples_per_capture, len equals total captures."""
        meta = rx_default.metadata
        expected = meta.total_samples // meta.interval
        assert len(rx_default) == expected

    def test_custom_interval(self, rx_small: Receiver) -> None:
        meta = rx_small.metadata
        assert len(rx_small) == meta.total_samples // meta.interval

    def test_positive(self, rx_default: Receiver) -> None:
        assert len(rx_default) > 0


# ---------------------------------------------------------------------------
# __getitem__ — shapes and dtypes
# ---------------------------------------------------------------------------


class TestGetItem:
    def test_returns_iqdata(self, rx_default: Receiver) -> None:
        assert isinstance(rx_default[0], IQData)

    def test_iq_shape(self, rx_default: Receiver) -> None:
        sample = rx_default[0]
        assert sample.iq.shape == (1, rx_default.metadata.interval)

    def test_iq_shape_custom_interval(self, rx_small: Receiver) -> None:
        sample = rx_small[0]
        assert sample.iq.shape == (1, 4096)

    def test_timestamps_shape(self, rx_default: Receiver) -> None:
        sample = rx_default[0]
        assert sample.timestamps.shape == (1,)

    def test_iq_dtype(self, rx_default: Receiver) -> None:
        assert rx_default[0].iq.dtype == np.complex64

    def test_timestamps_dtype(self, rx_default: Receiver) -> None:
        assert rx_default[0].timestamps.dtype == np.float64

    def test_last_index(self, rx_default: Receiver) -> None:
        """Reading the last item must not raise."""
        sample = rx_default[len(rx_default) - 1]
        assert sample.iq.shape == (1, rx_default.metadata.interval)

    def test_numpy_integer_index(self, rx_default: Receiver) -> None:
        """Sensor must accept np.integer indices."""
        sample = rx_default[np.intp(0)]
        assert sample.iq.shape == (1, rx_default.metadata.interval)


# ---------------------------------------------------------------------------
# Timestamps
# ---------------------------------------------------------------------------


class TestTimestamps:
    def test_monotonically_increasing(self, rx_default: Receiver) -> None:
        ts = rx_default.metadata.timestamps
        assert np.all(np.diff(ts) > 0)

    def test_getitem_timestamp_matches_metadata(
        self, rx_default: Receiver
    ) -> None:
        for idx in (0, 1, len(rx_default) - 1):
            sample = rx_default[idx]
            assert sample.timestamps[0] == rx_default.metadata.timestamps[idx]

    def test_default_interval_timestamps_match_capture_timestamps(
        self, rx_path: str, rx_default: Receiver
    ) -> None:
        """At the default interval the interpolated timestamps are exact."""
        capture_ts = np.fromfile(f"{rx_path}/ts.f8", dtype="<f8")
        n = len(rx_default)
        np.testing.assert_array_equal(
            rx_default.metadata.timestamps, capture_ts[:n]
        )


# ---------------------------------------------------------------------------
# Consistency
# ---------------------------------------------------------------------------


class TestConsistency:
    def test_consecutive_reads_are_contiguous(self, rx_path: str) -> None:
        """Two consecutive reads of interval k equal one read of interval 2k."""
        k = 512
        rx_k = Receiver(rx_path, interval=k)
        rx_2k = Receiver(rx_path, interval=2 * k)

        combined = np.concatenate([rx_k[0].iq, rx_k[1].iq], axis=1)
        np.testing.assert_array_equal(combined, rx_2k[0].iq)

    def test_chunk_boundary_crossing(self, rx_path: str) -> None:
        """Reading an item that straddles a chunk boundary."""
        interval = 4096
        rx = Receiver(rx_path, interval=interval)
        meta = rx.metadata

        # Index of the item that crosses the first chunk boundary.
        boundary = meta.samples_per_chunk
        idx = boundary // interval  # item whose range contains `boundary`

        sample = rx[idx]
        assert sample.iq.shape == (1, interval)
        assert sample.timestamps.shape == (1,)
