# Legacy Commands (v1.x)

⚠️ **DEPRECATED**: This folder contains all v1.x commands that are deprecated in v2.0 and **will be removed in v2.1**.

## Structure

```
legacy/
├── __init__.py      # Exports all legacy commands
├── full.py          # Complete v1.x command implementation (2,766 lines)
└── README.md        # This file
```

## Deprecated Commands

### Dataset Management (v1.x)
- `ddoc dataset add`
- `ddoc dataset commit`
- `ddoc dataset status`
- `ddoc dataset list`
- `ddoc dataset timeline`
- `ddoc dataset checkout`
- `ddoc dataset tag list/rename`
- `ddoc dataset unstage`

**→ Replaced by**: `ddoc add`, `ddoc snapshot`, workspace-centric v2.0 approach

### Lineage Tracking (v1.x)
- `ddoc lineage show`
- `ddoc lineage graph`
- `ddoc lineage overview`
- `ddoc lineage impact`
- `ddoc lineage dependencies`
- `ddoc lineage dependents`

**→ Replaced by**: `ddoc snapshot --graph`, snapshot-based lineage

### Top-level Deprecated Commands
- `ddoc commit` → `ddoc snapshot -m`
- `ddoc checkout` → `ddoc snapshot --restore`
- `ddoc log` → `ddoc snapshot --list`
- `ddoc status` → `git status` (use native Git)
- `ddoc alias` → `ddoc snapshot --set-alias/--unalias`
- `ddoc diff` → `ddoc snapshot --diff`

### Experiment Commands
- `ddoc exp run/list/show/compare/status/best`

**Note**: These are in legacy temporarily. They will be refactored to v2.0 style in a future update and moved out of legacy.

## Migration Path

### v2.0 (Current)
- Legacy commands are **hidden** but still functional
- Users should migrate to new snapshot-based workflow
- `full.py` contains complete v1.x implementation

### v2.1 (Planned)
- This entire `legacy/` folder will be **deleted**
- Only v2.0 commands will remain
- Breaking changes for users still on v1.x commands

## For Developers

### Adding/Modifying Legacy Commands
**Don't.** These commands are frozen and will be removed in v2.1.

### Migrating Experiment Commands
When refactoring experiment commands to v2.0 style:
1. Create `ddoc/cli/commands/experiment/` modules
2. Import and adapt logic from `legacy/full.py`
3. Remove experiment commands from `legacy/__init__.py`
4. Update `commands/__init__.py` imports

### Removing Legacy (v2.1)
```bash
# When v2.1 arrives:
rm -rf ddoc/cli/commands/legacy/
# Update commands/__init__.py to remove legacy imports
# Update CHANGELOG and migration guide
```

## Rationale

Why keep legacy commands in v2.0?
- **Backwards compatibility**: Users can migrate gradually
- **Documentation**: Easy to show old vs new commands
- **Safety**: Complete removal in v2.1 after users have migrated

Why put them in a separate folder?
- **Clear separation**: v2.0 core vs v1.x legacy
- **Easy removal**: Delete entire folder in v2.1
- **Organization**: Prevents mixing old and new patterns

---

**Last Updated**: 2025-11-17 (v2.0.0 release)

