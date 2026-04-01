# Issabel Operations Runbook

## Overview

This runbook describes how the local Issabel development stack is built, started, verified and maintained.

## Build flow

1. [`scripts/prepare-iso-root.sh`](/home/vasqs/Projetos/Issabel/scripts/prepare-iso-root.sh) extracts the local ISO content needed for package installation into `.build/issabel-root`.
2. [`docker/issabel/Dockerfile`](/home/vasqs/Projetos/Issabel/docker/issabel/Dockerfile) builds a CentOS 7 based image and installs Issabel packages from `file:///opt/issabel-root`.
3. [`docker-compose.yml`](/home/vasqs/Projetos/Issabel/docker-compose.yml) runs the resulting image as `issabel-dev`.

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
- marking first boot complete through `/var/lib/issabel/.bootstrapped`

The web admin reconciliation runs before the marker check, so changing `.env` and recreating the container rotates the Issabel web password without deleting volumes.

## Environment variables

Defined in [.env](/home/vasqs/Projetos/Issabel/.env) and referenced by [`docker-compose.yml`](/home/vasqs/Projetos/Issabel/docker-compose.yml):

- `ISSABEL_WEB_ADMIN_USER`
- `ISSABEL_WEB_ADMIN_PASSWORD`

Current defaults in [.env.example](/home/vasqs/Projetos/Issabel/.env.example):

```env
ISSABEL_WEB_ADMIN_USER=admin
ISSABEL_WEB_ADMIN_PASSWORD=DevAdmin123
```

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
