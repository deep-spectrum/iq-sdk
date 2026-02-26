"""Dataloaders and utilities for I/Q radio recordings.

# Usage

## Loading a receiver

[`Receiver`][iq_sdk.Receiver] reads I/Q data from a single receiver directory
produced by the [recording format](format.md). Pass the path to the `rx*`
subdirectory and, optionally, an `interval` controlling how many samples are
returned per item.

```python
from iq_sdk import Receiver

# Default interval — one item per capture (samples_per_capture samples each).
rx = Receiver("data/lab_noise/rx0")

# Custom interval — 4096 samples per item.
rx = Receiver("data/lab_noise/rx0", interval=4096)
```

## Indexing

[`Receiver`][iq_sdk.Receiver] implements the
[abstract-dataloader](https://radarml.github.io/abstract-dataloader/)
[`Sensor`][abstract_dataloader.spec.Sensor] protocol, so items are accessed by
integer index:

```python
sample = rx[0]          # IQData[np.ndarray]
print(sample.iq)        # complex64 array, shape (1, interval)
print(sample.timestamps) # float64 array, shape (1,)
```

## Iterating

```python
for sample in rx.stream():
    process(sample.iq, sample.timestamps)
```

## Inspecting metadata

All receiver-level state is stored in `rx.metadata`:

```python
meta = rx.metadata
print(meta.interval)           # samples per item
print(meta.total_samples)      # total I/Q samples in the recording
print(meta.samples_per_chunk)  # samples per on-disk chunk file
print(meta.chunks)             # sorted list of chunk file paths
print(meta.timestamps)         # float64 array, one epoch second per item
```
"""

from iq_sdk.dataloader import IQData, Receiver, ReceiverMetadata

__all__ = ["IQData", "Receiver", "ReceiverMetadata"]
