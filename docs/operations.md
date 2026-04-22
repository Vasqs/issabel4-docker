# Issabel Operations Runbook

## Overview

This runbook describes how the Issabel stack is built, started, verified and maintained across the supported Docker network modes.

## Compose modes and network contract

The repository supports two mutually exclusive compose layouts:

- `bridge` uses [`docker-compose.yml`](/mnt/a50116fc-d882-495c-9386-3c0c4b164506/Projects/Issabel/docker-compose.yml) and Docker `ports:` publishing
- `hostnet` uses [`docker-compose.hostnet.yml`](/mnt/a50116fc-d882-495c-9386-3c0c4b164506/Projects/Issabel/docker-compose.hostnet.yml) and `network_mode: host`

[`scripts/compose-mode.sh`](/mnt/a50116fc-d882-495c-9386-3c0c4b164506/Projects/Issabel/scripts/compose-mode.sh) resolves `ISSABEL_COMPOSE_MODE`, accepting shell flags and falling back to `.env` when the variable is unset. The operational helpers inherit that selection:

- [`scripts/up.sh`](/mnt/a50116fc-d882-495c-9386-3c0c4b164506/Projects/Issabel/scripts/up.sh)
- [`scripts/down.sh`](/mnt/a50116fc-d882-495c-9386-3c0c4b164506/Projects/Issabel/scripts/down.sh)
- [`scripts/diagnose.sh`](/mnt/a50116fc-d882-495c-9386-3c0c4b164506/Projects/Issabel/scripts/diagnose.sh)

`bridge` is a lab-only mode. It is acceptable for local UI validation, quick module work, or isolated loopback tests, but Docker bridge NAT and published UDP ports can break production SIP semantics. The most common symptoms are wrong Contact or SDP addresses, one-way audio, missing DTMF, unstable re-INVITEs, or Janus receiving a Docker bridge address that it cannot reach.

`hostnet` is the supported production and homologation contract for SIP or Janus. Use it whenever Issabel must expose SIP/UDP and RTP directly on the host without Docker NAT:

```bash
ISSABEL_COMPOSE_MODE=hostnet ./scripts/up.sh
```

In `hostnet` mode there is no Docker `ports:` section. The container shares the host network stack, so the real host interfaces and routes are visible to SIP peers and to Janus. If your production platform cannot use Docker host networking, the equivalent requirement still applies: run Issabel with direct host networking or another runtime design that avoids Docker bridge NAT for SIP and RTP.

## Build flow

1. [`scripts/resolve-install-profile.py`](/home/vasqs/Projetos/Issabel/scripts/resolve-install-profile.py) resolves the guided installation profile.
2. [`scripts/prepare-iso-root.sh`](/home/vasqs/Projetos/Issabel/scripts/prepare-iso-root.sh) extracts the selected ISO content into `.build/issabel-root`.
3. [`docker/issabel/Dockerfile`](/home/vasqs/Projetos/Issabel/docker/issabel/Dockerfile) builds a CentOS 7 based image and installs Issabel packages from `file:///opt/issabel-root`.
4. [`docker-compose.yml`](/home/vasqs/Projetos/Issabel/docker-compose.yml) runs the resulting image as `issabel-dev` unless overridden by `.env`.

Repository note:

- when enabled for supported Asterisk versions, the image build rewrites `CentOS-Base.repo` to the AlmaLinux-hosted EL7 mirror `https://el7.repo.almalinux.org/centos/CentOS-Base.repo`
- this is a repository-source migration only; it does not run a full AlmaLinux OS conversion and does not force a system upgrade
- the IssabelBR payload is now applied during image build instead of container startup

## Guided installation flow

The installer wizard is a build-time flow.

1. detect available ISO files in the project root
2. choose the ISO if more than one is present
3. extract the selected ISO
4. detect available `asteriskXX` packages from the extracted repository
5. choose the Asterisk package first
6. choose the optional module profile and per-module adjustments second
7. choose whether to bake the IssabelBR payload into the image build
8. persist the result in `.issabel-install.conf`
9. generate `.build/install.env` for the build scripts
10. refresh `.env` so direct `docker compose` runs use the same wizard selection

Compatibility rule:

- `issabel-callcenter` is shown only when the selected Asterisk package is `asterisk11`

## Startup flow

On container start, [`bootstrap-issabel`](/home/vasqs/Projetos/Issabel/docker/issabel/rootfs/usr/local/bin/bootstrap-issabel) performs the runtime bootstrap in this order:

1. prepares filesystem paths and ownership
2. initializes MariaDB data directory if needed
3. starts MariaDB and waits for readiness
4. runs [`issabel-firstboot`](/home/vasqs/Projetos/Issabel/docker/issabel/rootfs/usr/local/bin/issabel-firstboot)
5. starts Apache and waits for HTTP readiness
6. starts Asterisk and waits for CLI readiness
7. regenerates and reloads PBX runtime config through `retrieve_conf` and `amportal a r`
8. monitors the three service PIDs

## First-boot responsibilities

[`issabel-firstboot`](/home/vasqs/Projetos/Issabel/docker/issabel/rootfs/usr/local/bin/issabel-firstboot) is responsible for:

- creating `asteriskcdrdb` if needed
- creating `mya2billing` if needed
- granting `asteriskuser@localhost` access with password `amp109`
- converging the MariaDB `root@localhost` password to the legacy Issabel value expected by privileged tooling
- reconciling `/etc/issabel.conf` with `mysqlrootpwd` and `amiadminpwd` for legacy backup and restore workflows
- reconciling the Issabel web admin user in `/var/www/db/acl.db`
- assigning that user to the `administrator` group if missing
- aligning `amportal.conf`, `issabelpbx.conf`, `dialerd.conf`, `manager.conf`, `sip_general_custom.conf`, `rtp_custom.conf`, and the HTTP redirect configuration
- restoring the IssabelPBX queue runtime stub in `/etc/asterisk/queues.conf` so `queues_additional.conf` is actually loaded
- aligning `call_center.valor_config` with the reconciled AMI credentials
- running `amportal chown` when available on the first pass of a container lifetime
- marking first boot complete through `/var/lib/issabel/.bootstrapped`

The web admin reconciliation runs before the marker check, so changing `.env` and recreating the container rotates the Issabel web password without deleting volumes.

Heavy provisioning now happens during image build through [`apply-issabelbr-build-assets`](/home/vasqs/Projetos/Issabel/docker/issabel/rootfs/usr/local/bin/apply-issabelbr-build-assets). That helper is responsible for package installation, repository rewrites, cloning `ibinetwork/IssabelBR`, and copying the static web, audio, and Asterisk payloads into the image before the container is created. The same build step also caches the applied IssabelBR payload under `/opt/issabelbr-runtime-assets` so it can be replayed later without rerunning package installation.

After a successful web-driven restore, the local override for [`issabel-helper`](/home/vasqs/Projetos/Issabel/docker/issabel/rootfs/usr/bin/issabel-helper) runs [`apply-issabelbr-post-restore`](/home/vasqs/Projetos/Issabel/docker/issabel/rootfs/usr/local/bin/apply-issabelbr-post-restore). That replay is intentionally runtime-safe: it reapplies the cached IssabelBR payload, reruns the Asterisk and web file reconciliations, invokes [`issabel-firstboot`](/home/vasqs/Projetos/Issabel/docker/issabel/rootfs/usr/local/bin/issabel-firstboot), and reloads `amportal`. The first-boot helper now also repairs the `call_center` schema if the `agent` table is missing, using the bundled `issabel-callcenter` SQL dump shipped in the image.

## Backup and restore contract

The bundled Issabel backup engine is legacy-oriented and expects runtime artifacts that are not obvious from the web UI alone.

- `/etc/issabel.conf` must exist and contain `mysqlrootpwd`
- `/etc/issabel.conf` should also contain `amiadminpwd` for legacy restore helpers
- MariaDB `root@localhost` must accept the same password stored in `mysqlrootpwd`
- `/tftpboot` must exist so the `endpoint/ep_config_files` component can be archived as `tftpboot.tgz`

The local runtime bootstrap now guarantees those conditions on container start. This prevents the two fatal backup errors seen during validation:

- `failed to find MySQL root password in /etc/issabel.conf`
- `endpoint/ep_config_files: failed to create tarball tftpboot.tgz`

Warnings about missing optional databases such as `roundcubedb`, `endpointconfig`, `qstats`, `sugarcrm`, `vtigercrm510`, or `meetme` are non-fatal. They indicate optional legacy components that are not installed in the current stack.

## Environment variables

Defined in [.env](/home/vasqs/Projetos/Issabel/.env) and referenced by [`docker-compose.yml`](/home/vasqs/Projetos/Issabel/docker-compose.yml):

- `ISSABEL_WEB_ADMIN_USER`
- `ISSABEL_WEB_ADMIN_PASSWORD`
- `ISSABEL_COMPOSE_MODE`
- `COMPOSE_PROJECT_NAME`
- `ISSABEL_CONTAINER_NAME`
- `ISSABEL_HOSTNAME`
- `ISSABEL_HTTP_PORT`
- `ISSABEL_HTTPS_PORT`
- `WORKSPACE_BIND_SOURCE`

Current defaults in [.env.example](/home/vasqs/Projetos/Issabel/.env.example):

```env
COMPOSE_PROJECT_NAME=issabel
ISSABEL_COMPOSE_MODE=bridge
ISSABEL_CONTAINER_NAME=issabel-dev
ISSABEL_HOSTNAME=issabel.local
ISSABEL_HTTP_PORT=8088
ISSABEL_HTTPS_PORT=8443
WORKSPACE_BIND_SOURCE=.
ISSABEL_WEB_ADMIN_USER=admin
ISSABEL_WEB_ADMIN_PASSWORD=DevAdmin123
```

Build-time selections are stored in the wizard artifacts:

- `.issabel-install.conf`
- `.build/install.env`
- `.env` is regenerated from those artifacts for Compose compatibility

## Endpoints

Bridge mode endpoints:

- `http://127.0.0.1:8088`
- `https://127.0.0.1:8443`

Hostnet mode endpoint contract:

- no Docker published ports
- web, SIP, and RTP listeners bind directly on the host network stack
- use the host IP or DNS directly and validate listeners with `./scripts/diagnose.sh` or `ss -ltnup`

Internal container listeners validated during setup:

- Apache on port `80`
- MariaDB on port `3306`
- Asterisk CLI through local socket

## Persistent storage

Named volumes used by the stack:

- `issabel-etc` for `/etc/asterisk`
- `issabel-var-lib` for `/var/lib/asterisk`
- `issabel-var-log` for `/var/log/asterisk`
- `issabel-mysql` for `/var/lib/mysql`
- `issabel-spool` for `/var/spool/asterisk`

These volumes keep the PBX and database stable across rebuilds and recreates.

## Development workflow

Recommended loop for module and integration work:

1. edit code in this repository
2. run `./scripts/sync-workspace.sh`
3. reload the relevant Issabel page or service
4. if needed, run `./scripts/diagnose.sh`

Sync targets:

- local `modules/<module>` to `/var/www/html/modules/<module>`
- local `integrations/` to `/opt/issabel-integrations`

### Local module contract

The module contract is explicit and sync-driven. A module is active when its directory exists under `modules/` and the user runs `./scripts/sync-workspace.sh`.

Recommended layout:

```text
modules/<module>/
  web/
  migrations/
    apply/<database>/*.sql
    revert/<database>/*.sql
  hooks/apply.sh
  hooks/revert.sh

overlays/<overlay>/web_root/
  index.php
  NewIvr/
    index.php
    login.php
```

Rules enforced by the sync helper:

- `web/` is published to `/var/www/html/modules/<module>`
- `overlays/<overlay>/web_root` is applied on top of `/var/www/html` and restored automatically when the overlay is removed
- if `web/` is missing, the module root itself is published as a legacy-compatible payload
- conflicting overlay targets across active overlays abort the sync before changes are applied
- `migrations/apply/<database>` are executed in lexicographic order and tracked in `/var/lib/asterisk/issabel-module-state`
- `migrations/revert/<database>` run in reverse order when a previously active module is removed and sync runs again
- `hooks/apply.sh` and `hooks/revert.sh` are optional and should be idempotent
- URL direta is the expected access pattern for custom modules in this stack, for example `http://127.0.0.1:8088/modules/<module>/...`

This is the project module contract for keeping Issabel customizations outside the stable base while preserving a reversible path for database and runtime changes.

## Verification commands

Useful checks:

```bash
docker compose ps
./scripts/diagnose.sh
docker exec issabel-dev bash -lc 'mysqladmin --socket=/var/lib/mysql/mysql.sock ping'
docker exec issabel-dev bash -lc 'curl -I -sS http://127.0.0.1/ | head -n 5'
docker exec issabel-dev bash -lc 'asterisk -rx "core show version" | head -n 2'
docker exec issabel-dev bash -lc 'sqlite3 -header -column /var/www/db/acl.db "select id,name,md5_password from acl_user;"'
```

For production SIP or Janus validation, run the same commands with `ISSABEL_COMPOSE_MODE=hostnet` and confirm there are no Docker-published SIP or RTP ports in the selected compose file.

## Password rotation

To rotate the Issabel web admin password:

1. update [.env](/home/vasqs/Projetos/Issabel/.env)
2. recreate the container:

```bash
docker compose up -d --build --force-recreate issabel
```

The bootstrap will update the admin hash in `/var/www/db/acl.db` automatically.

## Troubleshooting

### Container is not healthy

Run:

```bash
./scripts/diagnose.sh
docker logs issabel-dev
```

Focus on:

- MariaDB errors in `/var/log/mariadb/mariadb.log`
- Apache startup failures in `/var/log/issabel-httpd.log`
- Asterisk startup failures in `/var/log/issabel-asterisk.log`

### Web login fails

Check:

```bash
docker exec issabel-dev bash -lc 'sqlite3 -header -column /var/www/db/acl.db "select id,name,md5_password from acl_user where name = \"admin\";"'
```

Then compare the hash with the password in `.env`.

### MariaDB is up but Issabel behaves inconsistently

Remember that the web framework auth uses SQLite in `/var/www/db/acl.db`, not MariaDB. MariaDB is used for PBX-related data such as `asteriskcdrdb`.

### SIP or Janus works in the lab but breaks in production

Check the active compose mode first. If the stack is running in `bridge`, treat that as a likely root cause before tuning SIP peers. Published Docker UDP ports are not the production contract for this repository.

Move the stack to `hostnet`:

```bash
ISSABEL_COMPOSE_MODE=hostnet ./scripts/down.sh
ISSABEL_COMPOSE_MODE=hostnet ./scripts/up.sh
```

Then revalidate:

- `./scripts/diagnose.sh`
- `docker exec issabel-dev bash -lc 'asterisk -rx "sip show settings"'`
- confirm `ISSABEL_SIP_EXTERNAL_ADDRESS` points to a real host-reachable address
- confirm `ISSABEL_SIP_LOCALNETS` contains only networks that should bypass that external address
- confirm Janus or remote peers no longer see a Docker bridge address such as `172.x.x.x`

### Backup generation fails on `endpoint/ep_config_files`

If `backupengine` stops on `endpoint/ep_config_files` with a `tftpboot.tgz` tarball error, confirm that `/tftpboot` exists inside the container. The runtime bootstrap now creates that directory during startup because the legacy backup path expects it to be present.

The same backup path also expects the legacy credentials file at `/etc/issabel.conf` to contain `mysqlrootpwd`. This repository keeps that file synchronized during first boot so backup and restore can authenticate against MariaDB consistently.

### Workspace changes are not reflected

Run:

```bash
./scripts/sync-workspace.sh
```

Then inspect the target paths inside the container:

```bash
docker exec issabel-dev bash -lc 'ls -la /var/www/html/modules /opt/issabel-integrations'
```

## Portainer guidance

Portainer is acceptable for:

- viewing logs
- checking container health
- browsing volumes
- restarting the container

Portainer should not replace versioned configuration in [`docker-compose.yml`](/home/vasqs/Projetos/Issabel/docker-compose.yml) or [.env](/home/vasqs/Projetos/Issabel/.env).
