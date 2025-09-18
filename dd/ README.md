# dd

- JPark @ KETI

## Structure

```bash
dd/
  dd/
    __init__.py
    cli/                 # CLI commands (Typer/Click)
    core/                # Contracts(ABC), registries, events, pipeline engine
    io/                  # Data I/O, format adapters, storage backends
    data/                # Modality primitives (text, image, video, timeseries)
    ops/                 # EDA, transforms, drift, reconstruction, retraining, monitoring
    tracking/            # Metadata, lineage, experiment tracking
    runtime/             # Config, dependency injection, plugin loading, env
    utils/               # Common helpers, logging, parallel, telemetry
  plugins/
    dd-plugin-.../       # Optional: first-party plugins (e.g., kafka, s3, prometheus, xgboost)
  examples/
  tests/
  pyproject.toml
  README.md
```

### Interfaces

2.1 Common Interfaces (Contracts)
• DataSource: Access to raw data (file/DB/streaming)
• Dataset: Standardized data units in batch/stream format
• Schema: Definition and validation of columns/features
• Transform: Preprocessing/feature extraction/format conversion
• EDA: Summary/profiling/visualization output
• DriftDetector: Detect drift in data/features/model (output)
• Reconstructor: Restore/sample missing/corrupted data
• Trainer: Model training/retraining
• Monitor: Online/offline monitoring and notifications
• Tracker: Experiment/artifact/lineage records
• Pipeline: Execution graph (node/edge) that links the above elements
• EventBus: Publish-subscribe execution/alert events

For each interface, a contract is defined as ABC (or typing.Protocol), and implementations are provided as plugins.