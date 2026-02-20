# Data Format

```
unique_recording_name/
├── rx0/
│   ├── iq00.c8
│   ├── iq01.c8
│   ├── ...
│   ├── ts.f8
│   └── meta.yaml
├── rx1/
│   └── ...
├── tx0/
│   ├── ts.f8               (optional)
│   ├── signal.sigmf-meta   (optional)
│   ├── signal.sigmf-data   (optional)
│   ├── {field1}.{type}     (optional)
│   └── {field2}.{type}     (optional)
├── tx1/
│   └── ...
└── ...
```

## Recording Trace

Each trace is stored in a folder with a unique name.

- Trace folder names are not required to follow a specific format.

- Each trace folder contains one or more transmitter and receiver subfolders.
- Each trace may also contain metadata images for documentation.
    - These images should use a standard image format with a descriptive name and matching file extension.
    - Image names are not required to follow a specific format.

Each trace folder must contain a `meta.yaml` file.

- Exact field specifications TBD; for now this file is just used to denote the presence of a data trace.

## Receiver Data

Data from each receiver is stored in a folder with a unique name starting with `rx`. This name also acts as the receiver ID.

Data is stored in chunks (named `iq0.c8`, `iq1.c8`, `iq2.c8`, ...), each of which contains `captures_per_chunk` captures. Each capture in turn contains `samples_per_capture` complex I/Q samples.

!!! note

    While I/Q data is recorded in discrete chunks and captures, the captures are taken consecutively and continuously with no gaps between them.

!!! warning

    I/Q chunks may contain trailing zero-padding in order to align with page boundaries. Chunks should always be read up to `bytes_per_sample * samples_per_capture * captures_per_chunk`, where `bytes_per_sample = 8` for `complex64`.

This directory contains the following files:

| Filename | Type | Description |
| --- | --- | --- |
| `ts.f8` | `float64`, little-endian | Timestamps for each sample, in seconds (unix epoch time). |
| `iq(\d+).c8` | `complex64`, little-endian | Continuous time series of complex IQ samples. |
| `meta.yaml` | yaml / ascii | Receiver metadata. |

`meta.yaml` has the following fields:

| Field | Type | Description |
| --- | --- | --- |
| `device` | string | The device used to record the trace (`SM200C`, `SM435C`). |
| `captures` | int | The total number of captures recorded. |
| `samples_per_capture` | int | The number of samples in each capture. |
| `captures_per_chunk` | int | The number of captures in each chunk. |

!!! warning

    The format of `meta.yaml` is not finalized and subject to change.

## Transmitter Data

Data from each transmitter is stored in a folder with a unique name starting with `tx`. This name also acts as the transmitter ID.

Each transmitter folder must contain a `meta.yaml` file, which has the following fields:

!!! warning

    The format of `meta.yaml` is not yet determined.

The following file types may also be present:

- Structured metadata:

    | Filename | Type | Description |
    | --- | --- | --- |
    | `ts.f8` | `float64`, little-endian | Timestamps for each metadata entry, in seconds (unix epoch time). |
    | `{name}.{type}` | binary, little-endian | Structured metadata fields. |

- GNU radio data:

    | Filename | Type | Description |
    | --- | --- | --- |
    | `signal.sigmf-meta` | json / ascii | GNU radio metadata for the signal. |
    | `signal.sigmf-data` | binary | GNU radio data for the signal. |

    !!! tip

        If `global/core:datatype` in `signal.sigmf-meta` is `cf32_le`, then `signal.sigmf-data` contains `complex64` samples in little-endian format, and can be loaded using the same method as receiver I/Q data.
