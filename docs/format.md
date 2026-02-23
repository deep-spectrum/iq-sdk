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

| Field                                             | Type   | Description                                               |
|---------------------------------------------------|--------|-----------------------------------------------------------|
| `captures`                                        | int    | The total number of captures recorded.                    |
| `captures_per_chunk`                              | int    | The number of captures in each chunk.                     |
| `device_configurations.decimation`                | int    | The downsampling factor.                                  |
| `device_configurations.device`                    | string | The device used to record the trace (`SM200C`, `SM435C`). |
| `device_configurations.device_addr`               | string | The IP address of the device.                             |
| `device_configurations.gps_lock_timeout`          | int    | Timeout in seconds to wait for GPS lock.                  |
| `device_configurations.gps_model`                 | string | The GPS mode (e.g., `STATIONARY`).                        |
| `device_configurations.gps_timestamping`          | bool   | Whether GPS timestamping is enabled.                      |
| `device_configurations.host`                      | string | Host address used for communication.                      |
| `device_configurations.port`                      | int    | Network port used for communication.                      |
| `device_configurations.serial`                    | int    | Device serial number (`-1` if not specified).             |
| `device_configurations.software_filter`           | bool   | Whether software filtering is enabled.                    |
| `diagnostics.api_version`                         | string | Version of the API used during capture.                   |
| `diagnostics.device_diagnostics.currentInput`     | float  | Measured input current (A).                               |
| `diagnostics.device_diagnostics.currentOCXO`      | float  | Measured OCXO current (A).                                |
| `diagnostics.device_diagnostics.tempFPGAInternal` | float  | Internal FPGA temperature (°C).                           |
| `diagnostics.device_diagnostics.tempFPGANear`     | float  | Temperature near FPGA (°C).                               |
| `diagnostics.device_diagnostics.tempOCXO`         | float  | OCXO temperature (°C).                                    |
| `diagnostics.device_diagnostics.tempPowerSupply`  | float  | Power supply temperature (°C).                            |
| `diagnostics.device_diagnostics.tempRFBoardLO`    | float  | RF board LO temperature (°C).                             |
| `diagnostics.device_diagnostics.tempVCO`          | float  | VCO temperature (°C).                                     |
| `diagnostics.device_diagnostics.voltage`          | float  | Measured supply voltage (V).                              |
| `diagnostics.network_diagnostics.rxPower`         | float  | Received network power level (mW).                        |
| `diagnostics.network_diagnostics.temp`            | float  | Network component temperature (°C).                       |
| `diagnostics.network_diagnostics.txPower`         | float  | Transmitted network power level (mW).                     |
| `diagnostics.network_diagnostics.voltage`         | float  | Network component voltage (V).                            |
| `diagnostics.save_duration`                       | float  | Time taken to save the capture (seconds).                 |
| `diagnostics.capture_duration`                    | float  | The time taken to capture the data (seconds).             |
| `parameters.bandwidth`                            | float  | Capture bandwidth in Hz.                                  |
| `parameters.capture_duration`                     | float  | Duration of each capture in seconds.                      |
| `parameters.center_frequency`                     | float  | Center frequency in Hz.                                   |
| `parameters.stop_if_sample_loss`                  | bool   | Whether capture stops if sample loss is detected.         |
| `sample_loss`                                     | bool   | Indicates if sample loss occurred during capture.         |
| `samples_per_capture`                             | int    | The number of samples in each capture.                    |

!!! note

    If a diagnostic field is not present or the entry is `null`, then the device does not have the necessary hardware
    for that diagnostic reading.

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
