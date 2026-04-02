# Web root overlays contract

`overlays/` is the workspace entrypoint for customizations that must run directly on top of `/var/www/html`, while keeping the original Issabel core restorable.

Everything inside this directory is ignored by Git, except this document. An overlay becomes active when its directory exists under `overlays/` and the user runs:

```bash
./scripts/sync-workspace.sh
```

## Supported layout

```text
overlays/<overlay-name>/
  web_root/
    index.php
    config.php
    any/relative/path.php
```

## Runtime behavior

- `web_root/` is applied on top of `/var/www/html`
- original Issabel files are snapshotted before replacement
- files created only by the overlay are removed when the overlay is removed
- deleting the overlay directory and syncing restores the original core web files
- conflicting overlays on the same `/var/www/html/<path>` abort the sync
- overlay state is persisted under `/var/lib/asterisk/issabel-module-state/overlays`

## Rules

- use `overlays/` only for files that must live directly in the Issabel web root
- prefer `modules/` for standalone content under `/var/www/html/modules`
- keep overlay names stable so state tracking and rollback stay predictable
