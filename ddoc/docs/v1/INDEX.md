# ddoc v1.x Documentation (Legacy)

⚠️ **Notice**: ddoc v1.x is in maintenance mode. We recommend using [v2.0.3](../README.md) for new projects.

## Documentation Index

### User Guides
- [ddoc Core Documentation](README_ddoc.md) - Main user guide for v1.x
- [App Documentation](README_app.md) - Application and visualization features

### Developer Resources
- [Development Guide](DEVELOPMENT.md) - Setup and development workflow
- [Testing Guide](TESTING.md) - Testing guidelines and practices
- [Project Structure](PROJECT_STRUCTURE.md) - Codebase organization

## Key Differences from v2.0.0

v1.x uses a **dataset-centric** approach:
```bash
# v1.x workflow
ddoc dataset add my_data ./data
ddoc dataset commit -m "initial"
ddoc dataset tag my_data v1 baseline
ddoc dataset checkout my_data v1
```

v2.0.0 uses a **workspace-centric** approach:
```bash
# v2.0.0 workflow (recommended)
ddoc init myproject
ddoc add --data ./data
ddoc commit -m "initial" -a baseline
ddoc checkout baseline
```

## Migration to v2.0.0

For migrating from v1.x to v2.0.0, see the [Migration Guide](../migration/v1-to-v2.md).

Key benefits of v2.0.0:
- Simpler command structure
- Complete workspace reproducibility
- Git-like familiar workflow
- Automatic project scaffolding
- Better integration with Git and DVC

## Latest v1.x Release

[v1.3.6](../releases/v1.3.6.md) - Last stable release

## Support

v1.x is in maintenance mode:
- Only critical bug fixes will be provided
- No new features will be developed
- Community support available via GitHub Issues (tag: `v1.x`)

## Installation

```bash
# Install v1.3.6 (last v1.x release)
pip install ddoc==1.3.6
```

---

**Recommendation**: Use [v2.0.3](../README.md) for all new projects!

