"""Unit tests for iq_sdk.dataloader."""

import os

import numpy as np
import pytest
import yaml

from iq_sdk import IQData, Receiver, ReceiverMetadata

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_DATA_DIR = os.environ.get("IQ_TEST_DATA", "")


@pytest.fixture(scope="module")
def rx_path() -> str:
    """Path to the receiver directory under IQ_TEST_DATA."""
    if not _DATA_DIR:
        pytest.skip("IQ_TEST_DATA environment variable is not set.")
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
    """Receiver.metadata fields and types."""

    def test_type(self, rx_default: Receiver) -> None:
        assert isinstance(rx_default.metadata, ReceiverMetadata)

    def test_timestamps_dtype(self, rx_default: Receiver) -> None:
        assert rx_default.metadata.timestamps.dtype == np.float64

    def test_timestamps_length_matches_len(self, rx_default: Receiver) -> None:
        assert len(rx_default.metadata.timestamps) == len(rx_default)

    def test_chunks_sorted(self, rx_default: Receiver) -> None:
        """Chunk files must be in ascending numeric order."""
        indices = [Receiver._chunk_index(c) for c in rx_default.metadata.chunks]
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
    """len(Receiver) for default and custom intervals."""

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
    """Receiver.__getitem__ output shapes and dtypes."""

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
    """Per-interval timestamp interpolation and ordering."""

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
    """Reads are contiguous and consistent across intervals/boundaries."""

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


# ---------------------------------------------------------------------------
# Chunk ordering — synthetic recordings, no external data required.
# ---------------------------------------------------------------------------


def _write_synthetic(
    root: str, *, n_chunks: int, spc: int, fs: float = 1e6
) -> str:
    """Write a synthetic recording (1 capture/chunk) under ``root/rx0``.

    Each chunk holds a distinct ascending ramp, so reading the recording back
    out of order is detectable byte-for-byte. Chunk files are *unpadded*
    (``iq0.c8`` .. ``iq{n}.c8``), matching real recordings. Returns the rx dir.
    """
    rx = os.path.join(root, "rx0")
    os.makedirs(rx)
    total = n_chunks * spc
    ramp = np.arange(total, dtype=np.float32).astype("<c8")
    for c in range(n_chunks):
        ramp[c * spc : (c + 1) * spc].tofile(os.path.join(rx, f"iq{c}.c8"))
    (1.7e9 + np.arange(n_chunks) * (spc / fs)).astype("<f8").tofile(
        os.path.join(rx, "ts.f8")
    )
    with open(os.path.join(rx, "meta.yaml"), "w") as f:
        yaml.safe_dump(
            {
                "captures": n_chunks,
                "captures_per_chunk": 1,
                "samples_per_capture": spc,
                "parameters": {"center_frequency": 1e8},
            },
            f,
        )
    return rx


class TestChunkIndex:
    """The sort key must read the index from the *filename*, not the path."""

    def test_basic(self) -> None:
        assert Receiver._chunk_index("/x/iq0.c8") == 0
        assert Receiver._chunk_index("/x/iq7.c8") == 7
        assert Receiver._chunk_index("/x/iq36.c8") == 36

    def test_ignores_c8_extension_digit(self) -> None:
        # The ``8`` in ``.c8`` must not be picked up.
        assert Receiver._chunk_index("iq0.c8") == 0

    def test_ignores_digits_elsewhere_in_path(self) -> None:
        # Digits in parent dirs must not influence the index (the original bug).
        ix = Receiver._chunk_index
        assert ix("/data0/run-6-18-26/2.45GHz/rx1/iq3.c8") == 3
        assert ix("/data0/run-6-18-26/2.45GHz/rx1/iq12.c8") == 12

    def test_rejects_malformed_name(self) -> None:
        # A name that is not exactly iq<N>.c8 must raise, not silently sort.
        for bad in ("iq.c8", "iqx.c8", "chunk0.c8", "iq0.bin", "iq0_extra.c8"):
            with pytest.raises(ValueError, match="iq<N>.c8"):
                Receiver._chunk_index(bad)


class TestChunkOrdering:
    """Regression for the path-digit chunk-sort bug.

    Chunks were sorted by the first digit-run of the full path, so any digit
    in the path collapsed the key and the order fell back to arbitrary
    ``glob`` (filesystem) order -- corrupting every read.
    """

    def test_digit_laden_path_sorts_numerically(self, tmp_path) -> None:
        # Path components contain digits the way real recordings do.
        root = tmp_path / "data0" / "lab_mod_switching_3-6-18-26" / "noisy"
        rx = _write_synthetic(str(root), n_chunks=37, spc=256)
        meta = Receiver(rx, interval=256).metadata
        indices = [Receiver._chunk_index(c) for c in meta.chunks]
        assert indices == list(range(37))

    def test_unpadded_names_not_string_sorted(self, tmp_path) -> None:
        # Numeric (not lexicographic) order: iq2 must precede iq10.
        rx = _write_synthetic(str(tmp_path / "rec1"), n_chunks=12, spc=256)
        chunks = Receiver(rx, interval=256).metadata.chunks
        names = [os.path.basename(c) for c in chunks]
        assert names == [f"iq{i}.c8" for i in range(12)]
        assert names.index("iq2.c8") < names.index("iq10.c8")

    def test_data_reads_in_true_order(self, tmp_path) -> None:
        # The decisive check: the recording reads back as the original ramp.
        spc, n = 256, 20
        rx = _write_synthetic(
            str(tmp_path / "data3" / "x9"), n_chunks=n, spc=spc
        )
        recv = Receiver(rx, interval=spc)
        got = np.concatenate([recv[i].iq[0] for i in range(len(recv))])
        expected = np.arange(spc * n, dtype=np.float32).astype(np.complex64)
        np.testing.assert_array_equal(got, expected)

    def test_short_final_chunk_lands_last(self, tmp_path) -> None:
        """A short final chunk must remain last so per-chunk length math holds.

        With a scrambled order the short chunk could land mid-list, and a
        read would over-run a chunk file. Here it reads cleanly end to end.
        """
        # 3 captures/chunk, 7 captures => last chunk is short (1 capture).
        rx = os.path.join(str(tmp_path / "set2"), "rx0")
        os.makedirs(rx)
        spc, cpc, captures = 256, 3, 7
        total = captures * spc
        ramp = np.arange(total, dtype=np.float32).astype("<c8")
        spchunk = cpc * spc
        n_chunks = (captures + cpc - 1) // cpc
        for c in range(n_chunks):
            block = ramp[c * spchunk : (c + 1) * spchunk]
            block.tofile(os.path.join(rx, f"iq{c}.c8"))
        (1.7e9 + np.arange(captures) * (spc / 1e6)).astype("<f8").tofile(
            os.path.join(rx, "ts.f8")
        )
        with open(os.path.join(rx, "meta.yaml"), "w") as f:
            yaml.safe_dump(
                {
                    "captures": captures,
                    "captures_per_chunk": cpc,
                    "samples_per_capture": spc,
                    "parameters": {"center_frequency": 1e8},
                },
                f,
            )
        recv = Receiver(rx, interval=spc)
        last = os.path.basename(recv.metadata.chunks[-1])
        assert last == f"iq{n_chunks - 1}.c8"
        got = np.concatenate([recv[i].iq[0] for i in range(len(recv))])
        np.testing.assert_array_equal(got, ramp.astype(np.complex64))

    def test_duplicate_index_raises(self, tmp_path) -> None:
        # iq0.c8 and iq00.c8 both resolve to index 0 -> ambiguous order.
        rx = _write_synthetic(str(tmp_path / "dup"), n_chunks=3, spc=256)
        np.zeros(256, dtype="<c8").tofile(os.path.join(rx, "iq00.c8"))
        with pytest.raises(ValueError, match="Duplicate chunk indices"):
            Receiver(rx, interval=256)

    def test_malformed_chunk_name_raises(self, tmp_path) -> None:
        # A stray iq*.c8 file that is not iq<N>.c8 must fail loudly.
        rx = _write_synthetic(str(tmp_path / "bad"), n_chunks=3, spc=256)
        np.zeros(256, dtype="<c8").tofile(os.path.join(rx, "iqbad.c8"))
        with pytest.raises(ValueError, match="iq<N>.c8"):
            Receiver(rx, interval=256)
