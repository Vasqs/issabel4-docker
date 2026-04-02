#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ISO_NAME="${ISO_NAME:-issabel4-NIGHTLY-AST18-USB-DVD-x86_64-20211207.iso}"
ISO_PATH="${ROOT_DIR}/${ISO_NAME}"
BUILD_DIR="${ROOT_DIR}/.build/issabel-root"

if [ ! -f "$ISO_PATH" ]; then
  echo "ISO not found at $ISO_PATH" >&2
  exit 1
fi

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"
bsdtar -xf "$ISO_PATH" -C "$BUILD_DIR" \
  repodata repodata/* \
  Issabel Issabel/* \
  RPM-GPG-KEY-Issabel RPM-GPG-KEY-CentOS-7 RPM-GPG-KEY-EPEL-7
printf '%s\n' "$ISO_NAME" > "${BUILD_DIR}/.source-iso"
echo "Prepared local Issabel repository at ${BUILD_DIR}"
