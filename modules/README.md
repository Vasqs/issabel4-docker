# Standalone modules contract

`modules/` is the workspace entrypoint for standalone Issabel additions that should be published under `/var/www/html/modules/<module-name>`.

Everything inside this directory is ignored by Git, except this document. A module becomes active when its directory exists under `modules/` and the user runs:

```bash
./scripts/sync-workspace.sh
```

## Supported module layouts

Recommended layout for new modules:

```text
modules/<module-name>/
  web/
  migrations/
    apply/
      <database>/
        001_description.sql
    revert/
      <database>/
        001_description.sql
  hooks/
    apply.sh
    revert.sh
  module.env.example
```

Legacy layout is also supported. If a module does not provide `web/`, the sync script publishes the module root itself as the web payload and excludes only contract directories such as `migrations/` and `hooks/`.

If a customization needs to behave like a theme on top of the Issabel web root, use `overlays/<overlay-name>/web_root/` instead of `modules/`.

## Runtime behavior

- `web/` is published to `/var/www/html/modules/<module-name>`
- `migrations/apply/<database>/*.sql` are executed in sorted order during sync
- `migrations/revert/<database>/*.sql` are executed in reverse order if the module is removed and a later sync is run
- `hooks/apply.sh` runs after publish and migration apply
- `hooks/revert.sh` runs before revert SQL when the module is removed
- state and logs are persisted in `/var/lib/asterisk/issabel-module-state`

## Rules

- treat migration filenames as immutable once applied
- create a matching revert SQL file for every reversible apply SQL file
- keep hooks idempotent and safe to rerun
- prefer direct URLs for custom module entrypoints in this stack
- keep module-specific secrets or overrides in ignored files such as `module.env`
