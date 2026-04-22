# Issabel Docker Dev Stack

This project packages Issabel 4 for Docker-based development, lab validation and production-like SIP testing using the local ISO as the source repository for installation packages. The container runs MariaDB, Apache and Asterisk in a single service, while the project workspace is mounted into the container for plugin and integration development.

## What this stack provides

- local image build from `issabel4-NIGHTLY-AST18-USB-DVD-x86_64-20211207.iso`
- persistent MariaDB, Asterisk config and runtime state through Docker volumes
- bridge-mode local web access on `http://127.0.0.1:8088` and `https://127.0.0.1:8443`
- host-network compose mode for production SIP/Janus traffic without Docker NAT
- mounted workspace at `/workspace`
- controlled sync of development assets into the Issabel runtime
- reproducible web admin credentials from `.env`
- guided build-time selection of Asterisk and optional RPM modules
- local module contract with reversible apply and revert on `./scripts/sync-workspace.sh`

## Repository layout

- [`docker-compose.yml`](/home/vasqs/Projetos/Issabel/docker-compose.yml): main runtime definition
- [`docker-compose.hostnet.yml`](/mnt/a50116fc-d882-495c-9386-3c0c4b164506/Projects/Issabel/docker-compose.hostnet.yml): production-oriented host-network runtime definition
- [`docker/issabel/Dockerfile`](/home/vasqs/Projetos/Issabel/docker/issabel/Dockerfile): local image build
- [`docker/issabel/rootfs/usr/local/bin/bootstrap-issabel`](/home/vasqs/Projetos/Issabel/docker/issabel/rootfs/usr/local/bin/bootstrap-issabel): runtime process supervisor
- [`docker/issabel/rootfs/usr/local/bin/issabel-firstboot`](/home/vasqs/Projetos/Issabel/docker/issabel/rootfs/usr/local/bin/issabel-firstboot): first-boot and credential reconciliation
- [`docker/issabel/rootfs/usr/local/bin/apply-issabelbr-build-assets`](/home/vasqs/Projetos/Issabel/docker/issabel/rootfs/usr/local/bin/apply-issabelbr-build-assets): build-time IssabelBR package and asset integration
- [`scripts/resolve-install-profile.py`](/home/vasqs/Projetos/Issabel/scripts/resolve-install-profile.py): guided installer for ISO, Asterisk package and optional modules
- [`scripts/up.sh`](/home/vasqs/Projetos/Issabel/scripts/up.sh): build and start stack
- [`scripts/build-image.sh`](/home/vasqs/Projetos/Issabel/scripts/build-image.sh): build image only
- [`scripts/down.sh`](/home/vasqs/Projetos/Issabel/scripts/down.sh): stop stack
- [`scripts/diagnose.sh`](/home/vasqs/Projetos/Issabel/scripts/diagnose.sh): inspect processes, listeners and logs
- [`scripts/sync-workspace.sh`](/home/vasqs/Projetos/Issabel/scripts/sync-workspace.sh): sync local modules and integrations
- [`docs/operations.md`](/home/vasqs/Projetos/Issabel/docs/operations.md): full operational runbook

## Prerequisites

- Docker daemon running locally
- Docker Compose available through `docker compose`
- `bsdtar` available on the host
- local ISO present at [`issabel4-NIGHTLY-AST18-USB-DVD-x86_64-20211207.iso`](/home/vasqs/Projetos/Issabel/issabel4-NIGHTLY-AST18-USB-DVD-x86_64-20211207.iso)

## Quick start

Default quick start uses the lab-oriented `bridge` compose mode.

1. Copy `.env.example` if you want a fresh env file:
   `cp .env.example .env`
2. Copy `.issabel-install.conf.example` if you want to preseed the build profile:
   `cp .issabel-install.conf.example .issabel-install.conf`
3. Review the runtime values in [.env](/home/vasqs/Projetos/Issabel/.env).
4. Start the stack:
   `./scripts/up.sh`
5. In interactive terminals the installer will ask for the Asterisk version first and only then show compatible optional modules.
6. Open:
   `http://127.0.0.1:8088`
   `https://127.0.0.1:8443`

## Network modes

The repository supports two Docker network contracts through `ISSABEL_COMPOSE_MODE`:

- `bridge` is the default lab mode and uses [`docker-compose.yml`](/mnt/a50116fc-d882-495c-9386-3c0c4b164506/Projects/Issabel/docker-compose.yml) with published ports
- `hostnet` is the production-oriented mode and uses [`docker-compose.hostnet.yml`](/mnt/a50116fc-d882-495c-9386-3c0c4b164506/Projects/Issabel/docker-compose.hostnet.yml) with `network_mode: host`

Bridge mode is convenient for local web access, but it is not the correct production architecture for SIP/UDP or Janus. Docker bridge NAT and published UDP ports can rewrite or hide the real transport path, which is enough to break SIP contact addresses, re-INVITEs, RTP flow, DTMF, or Janus media even when a first registration appears to work.

Use `hostnet` in production, homologation, or any environment where Issabel must speak SIP/UDP directly to phones, trunks, SBCs, or Janus:

```bash
ISSABEL_COMPOSE_MODE=hostnet ./scripts/up.sh
```

In `hostnet` mode Docker does not publish or NAT HTTP, HTTPS, SIP, or RTP ports. The container shares the host network stack, so peers see the host's real addresses instead of a Docker bridge address. If you deploy outside Docker host networking, the equivalent requirement is the same: no Docker bridge NAT between Issabel and the SIP or Janus peers.

Keep `bridge` for local lab work only:

```bash
ISSABEL_COMPOSE_MODE=bridge ./scripts/up.sh
```

Use this mode for isolated UI checks, module development, or quick local experiments where `127.0.0.1:8088` and published ports are acceptable. Do not treat successful lab registration in bridge mode as production proof for SIP or Janus.

## Guided installation profile

Build-time choices are kept out of `.env`.

- `.issabel-install.conf` stores the selected ISO, Asterisk package and optional module keys
- `.issabel-install.conf` also stores whether the IssabelBR payload should be baked into the image build
- `.build/install.env` is generated from that profile and sourced by the build scripts
- the wizard detects available `asteriskXX` packages directly from the ISO contents
- `callcenter` is shown only when the selected Asterisk package is `asterisk11`
- the IssabelBR build payload prompt defaults to enabled for new profiles
- when enabled, the image build rewrites `CentOS-Base.repo` to the AlmaLinux-hosted EL7 mirror without performing a full OS migration or upgrade
- non-interactive executions reuse the saved profile instead of prompting

## Credentials

Current defaults are defined in [.env](/home/vasqs/Projetos/Issabel/.env):

- `COMPOSE_PROJECT_NAME=issabel`
- `ISSABEL_COMPOSE_MODE=bridge`
- `ISSABEL_CONTAINER_NAME=issabel-dev`
- `ISSABEL_HOSTNAME=issabel.local`
- `ISSABEL_HTTP_PORT=8088`
- `ISSABEL_HTTPS_PORT=8443`
- `WORKSPACE_BIND_SOURCE=.`
- `ISSABEL_WEB_ADMIN_USER=admin`
- `ISSABEL_WEB_ADMIN_PASSWORD=DevAdmin123`

The bootstrap reconciles this web admin user into `/var/www/db/acl.db` on every container start. If you change these values, recreate the container:

`docker compose up -d --build --force-recreate issabel`

Runtime contract:

- `docker compose restart issabel` reuses the current container and does not revisit build-time provisioning
- `docker compose up -d --force-recreate issabel` creates a new container and reruns only lightweight first-boot reconciliation
- `docker compose down && docker compose up -d` also creates a new container and therefore reruns the same lightweight reconciliation path
- `./scripts/up.sh`, `./scripts/down.sh`, and `./scripts/diagnose.sh` resolve `ISSABEL_COMPOSE_MODE` and pick either `docker-compose.yml` or `docker-compose.hostnet.yml`

## Workspace exposure

The full project is mounted at `/workspace` inside the container. The sync helper publishes only the development targets that should affect the Issabel runtime:

- `/workspace/modules` to `/var/www/html/modules/<module>`
- `/workspace/integrations` to `/opt/issabel-integrations`

This avoids bind-mounting the whole Issabel application tree over `/var/www/html`, which is safer for local stability.

### Local module contract

`modules/` is the safe extension point for custom Issabel changes. Most local modules stay ignored by Git, while shared wrappers can also live there as sibling repositories in the working tree when the runtime sync contract depends on them.

- a directory under `modules/` becomes active when `./scripts/sync-workspace.sh` runs
- if the module contains `web/`, that directory is published as `/var/www/html/modules/<module>`
- if the customization lives under `overlays/<overlay>/web_root/`, those files are applied over `/var/www/html` like a reversible theme layer
- if `web/` is absent, the module root is published as-is, excluding `migrations/` and `hooks/`
- overlay conflicts on the same target path stop the sync with an explicit error
- `migrations/apply/<database>/*.sql` run on sync in sorted order
- `migrations/revert/<database>/*.sql` run automatically when a module is removed and sync runs again
- optional `hooks/apply.sh` and `hooks/revert.sh` support reversible file or service changes
- the `callcenter_bridge` workspace module exposes an HTTP wrapper around ECCP for callcenter automation and panel integration when that sibling repository is present in `modules/`

This keeps standalone modules separate from the stable Issabel base and makes rollback easier when a local customization causes problems. Removing the overlay directory and running sync restores the original Issabel web files that were overlaid.

## Persistent data

The stack stores state in named Docker volumes for:

- `/etc/asterisk`
- `/var/lib/asterisk`
- `/var/log/asterisk`
- `/var/lib/mysql`
- `/var/spool/asterisk`

That means container recreation does not wipe the PBX configuration or MariaDB state.

## Runtime model

The container does not rely on `systemd` to manage services. Instead, the entrypoint starts and monitors:

- `mysqld_safe`
- `httpd -DFOREGROUND`
- `asterisk -U asterisk -G asterisk -fvvvg`

After Apache and Asterisk are ready, the runtime bootstrap also runs `retrieve_conf` plus `amportal a r` so generated PBX artifacts such as `sip_additional.conf` are rebuilt on container startup instead of depending on a manual reload.
The first-boot reconciliation also restores the IssabelPBX `queues.conf` include stub when the runtime file has drifted back to the stock Asterisk version, preventing queue definitions from silently disappearing even though `queues_additional.conf` exists.

This was chosen because it is more reliable in Docker for this Issabel 4 base than trying to reproduce a full init system inside the container.

## Common commands

- build only: `./scripts/build-image.sh`
- start or rebuild: `./scripts/up.sh`
- resolve or refresh the saved install profile: `python3 ./scripts/resolve-install-profile.py`
- stop: `./scripts/down.sh`
- inspect current state: `./scripts/diagnose.sh`
- sync local modules and apply or revert their customizations: `./scripts/sync-workspace.sh`

## Portainer

Portainer is optional. Use it for observation only: logs, health, volumes, restarts, shell access. Do not make Portainer the source of truth for this environment. The authoritative configuration remains the selected compose file, either [`docker-compose.yml`](/home/vasqs/Projetos/Issabel/docker-compose.yml) or [`docker-compose.hostnet.yml`](/mnt/a50116fc-d882-495c-9386-3c0c4b164506/Projects/Issabel/docker-compose.hostnet.yml), plus [.env](/home/vasqs/Projetos/Issabel/.env).

## Verification status

The stack has been validated locally for:

- image build from the ISO-derived repository
- healthy container startup
- MariaDB readiness and seeded `asteriskcdrdb`
- Apache responding on port `8088`
- Asterisk responding to CLI commands
- web login with credentials from `.env`

For deeper operational details and troubleshooting, see [`docs/operations.md`](/home/vasqs/Projetos/Issabel/docs/operations.md).
