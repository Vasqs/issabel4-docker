# Issabel Docker Dev Stack

This project packages Issabel 4 for local development with Docker, using the local ISO as the source repository for installation packages. The container runs MariaDB, Apache and Asterisk in a single service, while the project workspace is mounted into the container for plugin and integration development.

## What this stack provides

- local image build from `issabel4-NIGHTLY-AST18-USB-DVD-x86_64-20211207.iso`
- persistent MariaDB, Asterisk config and runtime state through Docker volumes
- local web access on `http://127.0.0.1:8088` and `https://127.0.0.1:8443`
- mounted workspace at `/workspace`
- controlled sync of development assets into the Issabel runtime
- reproducible web admin credentials from `.env`
- guided build-time selection of Asterisk and optional RPM modules

## Repository layout

- [`docker-compose.yml`](/home/vasqs/Projetos/Issabel/docker-compose.yml): main runtime definition
- [`docker/issabel/Dockerfile`](/home/vasqs/Projetos/Issabel/docker/issabel/Dockerfile): local image build
- [`docker/issabel/rootfs/usr/local/bin/bootstrap-issabel`](/home/vasqs/Projetos/Issabel/docker/issabel/rootfs/usr/local/bin/bootstrap-issabel): runtime process supervisor
- [`docker/issabel/rootfs/usr/local/bin/issabel-firstboot`](/home/vasqs/Projetos/Issabel/docker/issabel/rootfs/usr/local/bin/issabel-firstboot): first-boot and credential reconciliation
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

## Guided installation profile

Build-time choices are kept out of `.env`.

- `.issabel-install.conf` stores the selected ISO, Asterisk package and optional module keys
- `.issabel-install.conf` also stores whether the IssabelBR post-install patch should run on first boot
- `.build/install.env` is generated from that profile and sourced by the build scripts
- the wizard detects available `asteriskXX` packages directly from the ISO contents
- `callcenter` is shown only when the selected Asterisk package is `asterisk11`
- the IssabelBR post-install patch prompt defaults to enabled for new profiles
- the runtime always rewrites `CentOS-Base.repo` to the AlmaLinux-hosted EL7 mirror without performing a full OS migration or upgrade
- non-interactive executions reuse the saved profile instead of prompting

## Credentials

Current defaults are defined in [.env](/home/vasqs/Projetos/Issabel/.env):

- `COMPOSE_PROJECT_NAME=issabel`
- `ISSABEL_CONTAINER_NAME=issabel-dev`
- `ISSABEL_HOSTNAME=issabel.local`
- `ISSABEL_HTTP_PORT=8088`
- `ISSABEL_HTTPS_PORT=8443`
- `WORKSPACE_BIND_SOURCE=.`
- `ISSABEL_WEB_ADMIN_USER=admin`
- `ISSABEL_WEB_ADMIN_PASSWORD=DevAdmin123`

The bootstrap reconciles this web admin user into `/var/www/db/acl.db` on every container start. If you change these values, recreate the container:

`docker compose up -d --build --force-recreate issabel`

## Workspace exposure

The full project is mounted at `/workspace` inside the container. The sync helper publishes only the development targets that should affect the Issabel runtime:

- `/workspace/modules` to `/var/www/html/modules`
- `/workspace/integrations` to `/opt/issabel-integrations`

This avoids bind-mounting the whole Issabel application tree over `/var/www/html`, which is safer for local stability.

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

This was chosen because it is more reliable in Docker for this Issabel 4 base than trying to reproduce a full init system inside the container.

## Common commands

- build only: `./scripts/build-image.sh`
- start or rebuild: `./scripts/up.sh`
- resolve or refresh the saved install profile: `python3 ./scripts/resolve-install-profile.py`
- stop: `./scripts/down.sh`
- inspect current state: `./scripts/diagnose.sh`
- sync local code into runtime: `./scripts/sync-workspace.sh`

## Portainer

Portainer is optional. Use it for observation only: logs, health, volumes, restarts, shell access. Do not make Portainer the source of truth for this environment. The authoritative configuration remains [`docker-compose.yml`](/home/vasqs/Projetos/Issabel/docker-compose.yml) plus [.env](/home/vasqs/Projetos/Issabel/.env).

## Verification status

The stack has been validated locally for:

- image build from the ISO-derived repository
- healthy container startup
- MariaDB readiness and seeded `asteriskcdrdb`
- Apache responding on port `8088`
- Asterisk responding to CLI commands
- web login with credentials from `.env`

For deeper operational details and troubleshooting, see [`docs/operations.md`](/home/vasqs/Projetos/Issabel/docs/operations.md).
