#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ASTERISK_FILE_PATTERN = re.compile(r"^(asterisk(?P<major>\d+))-(?P=major)[\w.\-]*\.x86_64\.rpm$")
PROFILE_PRESETS = {
    "minimal": [],
    "standard": ["reports", "endpointconfig"],
    "full": ["reports", "endpointconfig", "extras", "fax", "agenda", "callcenter"],
}
DEFAULT_INSTALL_ISSABELBR_POST_PATCH = True
ISSABELBR_POST_PATCH_SUPPORTED_MAJORS = {"11", "13"}


@dataclass(frozen=True)
class AsteriskPackage:
    package_name: str
    major: str
    rpm_path: Path


@dataclass(frozen=True)
class ModuleOption:
    key: str
    label: str
    package_name: str
    requires_major: str | None = None


@dataclass(frozen=True)
class InstallSelection:
    iso_name: str
    asterisk: AsteriskPackage
    module_profile: str
    module_keys: list[str]
    optional_packages: list[str]
    install_issabelbr_post_patch: bool


MODULE_OPTIONS = [
    ModuleOption("agenda", "Agenda", "issabel-agenda"),
    ModuleOption("callcenter", "Call Center", "issabel-callcenter", requires_major="11"),
    ModuleOption("endpointconfig", "Endpoint Config", "issabel-endpointconfig2"),
    ModuleOption("extras", "Extras", "issabel-extras"),
    ModuleOption("fax", "Fax", "issabel-fax"),
    ModuleOption("reports", "Reports", "issabel-reports"),
]


def discover_iso_candidates(project_root: Path) -> list[Path]:
    return sorted(path for path in project_root.glob("*.iso") if path.is_file())


def read_key_values(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values


def quote_value(value: str) -> str:
    return shlex.quote(value)


def write_key_values(path: Path, values: dict[str, str]) -> None:
    lines = [f"{key}={quote_value(value)}" for key, value in values.items()]
    path.write_text("\n".join(lines) + "\n")


def prepare_iso_root(project_root: Path, iso_name: str) -> None:
    env = os.environ.copy()
    env["ISO_NAME"] = iso_name
    subprocess.run(
        [str(project_root / "scripts" / "prepare-iso-root.sh")],
        cwd=project_root,
        env=env,
        check=True,
    )


def resolve_repo_dir(build_root: Path) -> Path:
    preferred = build_root / "Issabel"
    if preferred.exists():
        return preferred

    candidates = sorted(path for path in build_root.iterdir() if path.is_dir())
    for candidate in candidates:
        if any(candidate.glob("*.rpm")):
            return candidate
    raise FileNotFoundError(f"could not find extracted RPM repository in {build_root}")


def discover_asterisk_packages(build_root: Path) -> list[AsteriskPackage]:
    repo_dir = resolve_repo_dir(build_root)
    packages: dict[str, AsteriskPackage] = {}

    for rpm_path in sorted(repo_dir.glob("*.rpm")):
        match = ASTERISK_FILE_PATTERN.match(rpm_path.name)
        if not match:
            continue
        package_name = match.group(1)
        packages[package_name] = AsteriskPackage(
            package_name=package_name,
            major=match.group("major"),
            rpm_path=rpm_path,
        )

    return sorted(packages.values(), key=lambda item: int(item.major))


def package_is_available(build_root: Path, package_name: str) -> bool:
    repo_dir = resolve_repo_dir(build_root)
    patterns = [f"{package_name}-*.rpm", f"{package_name}_*.rpm"]
    return any(any(repo_dir.glob(pattern)) for pattern in patterns)


def available_module_options(build_root: Path, asterisk_major: str) -> dict[str, ModuleOption]:
    available: dict[str, ModuleOption] = {}
    for option in MODULE_OPTIONS:
        if option.requires_major and option.requires_major != asterisk_major:
            continue
        if package_is_available(build_root, option.package_name):
            available[option.key] = option
    return available


def issabelbr_post_patch_is_supported(asterisk_major: str) -> bool:
    return asterisk_major in ISSABELBR_POST_PATCH_SUPPORTED_MAJORS


def resolve_default_selection(
    repo_root: Path,
    preferred_asterisk_package: str | None,
    preferred_module_keys: list[str] | None,
    preferred_module_profile: str = "standard",
    iso_name: str = "",
    install_issabelbr_post_patch: bool = DEFAULT_INSTALL_ISSABELBR_POST_PATCH,
) -> InstallSelection:
    packages = discover_asterisk_packages(repo_root)
    if not packages:
        raise RuntimeError("no versioned asterisk packages were detected in the extracted ISO repository")

    by_name = {item.package_name: item for item in packages}
    selected_asterisk = by_name.get(preferred_asterisk_package or "", packages[-1])

    available_modules = available_module_options(repo_root, selected_asterisk.major)
    default_keys = PROFILE_PRESETS.get(preferred_module_profile, PROFILE_PRESETS["standard"])
    requested_keys = preferred_module_keys if preferred_module_keys is not None else default_keys
    selected_keys = [key for key in requested_keys if key in available_modules]
    selected_packages = [available_modules[key].package_name for key in selected_keys]
    install_issabelbr_post_patch = (
        install_issabelbr_post_patch and issabelbr_post_patch_is_supported(selected_asterisk.major)
    )

    return InstallSelection(
        iso_name=iso_name,
        asterisk=selected_asterisk,
        module_profile=preferred_module_profile if preferred_module_profile in PROFILE_PRESETS else "standard",
        module_keys=selected_keys,
        optional_packages=selected_packages,
        install_issabelbr_post_patch=install_issabelbr_post_patch,
    )


def parse_module_keys(raw_value: str) -> list[str]:
    if not raw_value:
        return []
    normalized = raw_value.replace(" ", ",")
    return [item for item in (part.strip() for part in normalized.split(",")) if item]


def parse_bool(raw_value: str | None, default: bool) -> bool:
    if raw_value is None:
        return default

    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


def choose_index(prompt: str, items: list[str], default_index: int) -> int:
    while True:
        default_number = default_index + 1
        raw_value = input(f"{prompt} [{default_number}]: ").strip()
        if not raw_value:
            return default_index
        if raw_value.isdigit():
            chosen_index = int(raw_value) - 1
            if 0 <= chosen_index < len(items):
                return chosen_index
        print(f"Enter a number between 1 and {len(items)}.", file=sys.stderr)


def choose_yes_no(prompt: str, default: bool) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    while True:
        raw_value = input(f"{prompt} {suffix}: ").strip().lower()
        if not raw_value:
            return default
        if raw_value in {"y", "yes"}:
            return True
        if raw_value in {"n", "no"}:
            return False
        print("Enter y or n.", file=sys.stderr)


def resolve_interactive_selection(
    build_root: Path,
    iso_name: str,
    initial_selection: InstallSelection,
) -> InstallSelection:
    packages = discover_asterisk_packages(build_root)
    asterisk_options = [f"Asterisk {item.major} ({item.package_name})" for item in packages]
    current_index = next(
        index for index, item in enumerate(packages) if item.package_name == initial_selection.asterisk.package_name
    )

    print("Asterisk versions detected in the selected ISO:")
    for index, label in enumerate(asterisk_options, start=1):
        print(f"  {index}. {label}")
    selected_asterisk = packages[choose_index("Choose the Asterisk version", asterisk_options, current_index)]

    profile_names = list(PROFILE_PRESETS.keys())
    profile_labels = {
        "minimal": "Minimal",
        "standard": "Standard",
        "full": "Full",
    }
    print("\nModule profiles:")
    for index, profile_name in enumerate(profile_names, start=1):
        print(f"  {index}. {profile_labels[profile_name]}")
    selected_profile = profile_names[
        choose_index("Choose the optional module profile", profile_names, profile_names.index(initial_selection.module_profile))
    ]

    available_modules = available_module_options(build_root, selected_asterisk.major)
    default_keys = [key for key in PROFILE_PRESETS[selected_profile] if key in available_modules]
    selected_keys: list[str] = []

    if available_modules:
        print("\nOptional modules compatible with this Asterisk version:")
        for option in sorted(available_modules.values(), key=lambda item: item.label):
            enabled = option.key in initial_selection.module_keys or option.key in default_keys
            if choose_yes_no(f"Install {option.label} ({option.package_name})?", enabled):
                selected_keys.append(option.key)
    else:
        print("\nNo optional curated modules were detected for this Asterisk version.")

    install_issabelbr_post_patch = False
    if issabelbr_post_patch_is_supported(selected_asterisk.major):
        install_issabelbr_post_patch = choose_yes_no(
            "\nApply IssabelBR post-install patch on first boot?",
            initial_selection.install_issabelbr_post_patch,
        )
    else:
        print("\nIssabelBR post-install patch is only available for Asterisk 11 and 13.")

    return InstallSelection(
        iso_name=iso_name,
        asterisk=selected_asterisk,
        module_profile=selected_profile,
        module_keys=selected_keys,
        optional_packages=[available_modules[key].package_name for key in selected_keys],
        install_issabelbr_post_patch=install_issabelbr_post_patch,
    )


def write_install_artifacts(
    profile_path: Path,
    env_path: Path,
    selection: InstallSelection,
) -> None:
    profile_values = {
        "ISO_NAME": selection.iso_name,
        "ASTERISK_PACKAGE": selection.asterisk.package_name,
        "MODULE_PROFILE": selection.module_profile,
        "OPTIONAL_MODULE_KEYS": ",".join(selection.module_keys),
        "INSTALL_ISSABELBR_POST_PATCH": "1" if selection.install_issabelbr_post_patch else "0",
    }
    write_key_values(profile_path, profile_values)

    env_values = {
        "ISSABEL_INSTALL_ISO_NAME": selection.iso_name,
        "ISSABEL_INSTALL_ASTERISK_PACKAGE": selection.asterisk.package_name,
        "ISSABEL_INSTALL_OPTIONAL_PACKAGES": " ".join(selection.optional_packages),
        "ISSABEL_INSTALL_MODULE_PROFILE": selection.module_profile,
        "ISSABEL_INSTALL_OPTIONAL_MODULE_KEYS": ",".join(selection.module_keys),
        "ISSABEL_INSTALL_ISSABELBR_POST_PATCH": "1" if selection.install_issabelbr_post_patch else "0",
    }
    profile_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_lines = [f"export {key}={quote_value(value)}" for key, value in env_values.items()]
    env_path.write_text("\n".join(env_lines) + "\n")


def run(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Resolve and persist the Issabel installation profile.")
    parser.add_argument("--project-root", default=Path(__file__).resolve().parents[1], type=Path)
    parser.add_argument("--profile", default=".issabel-install.conf")
    parser.add_argument("--env-file", default=".build/install.env")
    parser.add_argument("--non-interactive", action="store_true")
    args = parser.parse_args(argv)

    project_root = args.project_root.resolve()
    profile_path = project_root / args.profile
    env_path = project_root / args.env_file
    build_root = project_root / ".build" / "issabel-root"
    stored_profile = read_key_values(profile_path)
    interactive = sys.stdin.isatty() and not args.non_interactive

    isos = discover_iso_candidates(project_root)
    if not isos:
        raise SystemExit("no ISO files were found in the project root")

    iso_names = [path.name for path in isos]
    preferred_iso = os.environ.get("ISO_NAME") or stored_profile.get("ISO_NAME") or iso_names[0]
    if preferred_iso not in iso_names:
        preferred_iso = iso_names[0]

    selected_iso = preferred_iso
    if interactive and len(iso_names) > 1:
        print("ISO images detected:")
        for index, iso_name in enumerate(iso_names, start=1):
            print(f"  {index}. {iso_name}")
        selected_iso = iso_names[choose_index("Choose the ISO to use", iso_names, iso_names.index(preferred_iso))]

    prepare_iso_root(project_root, selected_iso)

    stored_module_keys = (
        parse_module_keys(stored_profile["OPTIONAL_MODULE_KEYS"])
        if "OPTIONAL_MODULE_KEYS" in stored_profile
        else None
    )

    initial_selection = resolve_default_selection(
        repo_root=build_root,
        preferred_asterisk_package=os.environ.get("ISSABEL_INSTALL_ASTERISK_PACKAGE")
        or stored_profile.get("ASTERISK_PACKAGE"),
        preferred_module_keys=stored_module_keys,
        preferred_module_profile=stored_profile.get("MODULE_PROFILE", "standard"),
        iso_name=selected_iso,
        install_issabelbr_post_patch=parse_bool(
            os.environ.get("ISSABEL_INSTALL_ISSABELBR_POST_PATCH")
            or stored_profile.get("INSTALL_ISSABELBR_POST_PATCH"),
            DEFAULT_INSTALL_ISSABELBR_POST_PATCH,
        ),
    )

    final_selection = (
        resolve_interactive_selection(build_root=build_root, iso_name=selected_iso, initial_selection=initial_selection)
        if interactive
        else initial_selection
    )

    write_install_artifacts(profile_path=profile_path, env_path=env_path, selection=final_selection)

    print(f"ISO: {final_selection.iso_name}")
    print(f"Asterisk: {final_selection.asterisk.package_name}")
    if final_selection.optional_packages:
        print(f"Optional packages: {' '.join(final_selection.optional_packages)}")
    else:
        print("Optional packages: none")
    print(f"Install profile written to {profile_path}")
    print(f"Build environment written to {env_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
