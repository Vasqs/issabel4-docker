# Issabel Operations Runbook

## Overview

This runbook describes how the local Issabel development stack is built, started, verified and maintained.

## Build flow

1. [`scripts/resolve-install-profile.py`](/home/vasqs/Projetos/Issabel/scripts/resolve-install-profile.py) resolves the guided installation profile.
2. [`scripts/prepare-iso-root.sh`](/home/vasqs/Projetos/Issabel/scripts/prepare-iso-root.sh) extracts the selected ISO content into `.build/issabel-root`.
3. [`docker/issabel/Dockerfile`](/home/vasqs/Projetos/Issabel/docker/issabel/Dockerfile) builds a CentOS 7 based image and installs Issabel packages from `file:///opt/issabel-root`.
4. [`docker-compose.yml`](/home/vasqs/Projetos/Issabel/docker-compose.yml) runs the resulting image as `issabel-dev` unless overridden by `.env`.

Repository note:

- the runtime rewrites `CentOS-Base.repo` to the AlmaLinux-hosted EL7 mirror `https://el7.repo.almalinux.org/centos/CentOS-Base.repo`
- this is a repository-source migration only; it does not run a full AlmaLinux OS conversion and does not force a system upgrade

## Guided installation flow

The installer wizard is a build-time flow.

1. detect available ISO files in the project root
2. choose the ISO if more than one is present
3. extract the selected ISO
4. detect available `asteriskXX` packages from the extracted repository
5. choose the Asterisk package first
6. choose the optional module profile and per-module adjustments second
7. choose whether to apply the IssabelBR post-install patch on first boot
8. persist the result in `.issabel-install.conf`
9. generate `.build/install.env` for the build scripts

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
7. monitors the three service PIDs

## First-boot responsibilities

[`issabel-firstboot`](/home/vasqs/Projetos/Issabel/docker/issabel/rootfs/usr/local/bin/issabel-firstboot) is responsible for:

- creating `asteriskcdrdb` if needed
- creating `mya2billing` if needed
- granting `asteriskuser@localhost` access with password `amp109`
- reconciling the Issabel web admin user in `/var/www/db/acl.db`
- assigning that user to the `administrator` group if missing
- running `amportal chown` when available
- syncing `/workspace/modules` and `/workspace/integrations`
- rewriting `CentOS-Base.repo` to the AlmaLinux-hosted EL7 mirror before any optional post-install logic
- downloading and executing the IssabelBR post-install patch when `ISSABEL_INSTALL_ISSABELBR_POST_PATCH=1`
- marking first boot complete through `/var/lib/issabel/.bootstrapped`

The web admin reconciliation runs before the marker check, so changing `.env` and recreating the container rotates the Issabel web password without deleting volumes.

## Environment variables

Defined in [.env](/home/vasqs/Projetos/Issabel/.env) and referenced by [`docker-compose.yml`](/home/vasqs/Projetos/Issabel/docker-compose.yml):

- `ISSABEL_WEB_ADMIN_USER`
- `ISSABEL_WEB_ADMIN_PASSWORD`
- `COMPOSE_PROJECT_NAME`
- `ISSABEL_CONTAINER_NAME`
- `ISSABEL_HOSTNAME`
- `ISSABEL_HTTP_PORT`
- `ISSABEL_HTTPS_PORT`
- `WORKSPACE_BIND_SOURCE`

Current defaults in [.env.example](/home/vasqs/Projetos/Issabel/.env.example):

```env
COMPOSE_PROJECT_NAME=issabel
ISSABEL_CONTAINER_NAME=issabel-dev
ISSABEL_HOSTNAME=issabel.local
ISSABEL_HTTP_PORT=8088
ISSABEL_HTTPS_PORT=8443
WORKSPACE_BIND_SOURCE=.
ISSABEL_WEB_ADMIN_USER=admin
ISSABEL_WEB_ADMIN_PASSWORD=DevAdmin123
```

Build-time selections are stored outside `.env`:

- `.issabel-install.conf`
- `.build/install.env`

## Endpoints

- `http://127.0.0.1:8088`
- `https://127.0.0.1:8443`

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

- local `modules/` to `/var/www/html/modules`
- local `integrations/` to `/opt/issabel-integrations`

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
