from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import shutil
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENTRY_POINTS = {"main.py", "studio_gui.py"}
IGNORE_DIRS = {
    ".git", ".idea", ".vscode", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".venv", "venv", "env", "_archive",
}
GENERATED_DIR_NAMES = {"cache", "output", "frames", "logs"}
SUSPECT_PATTERNS = (
    "_old", "_backup", "_bak", "_copy", "_test", "_tmp", "_temp",
    "_fixed", "_final", "_new", "_v1", "_v2", "_v3", "_v4", "_v5",
    "_v6", "_v7", "_v8", "_v9", "_v10", "_v11", "_v12", "_v13",
    "_v14", "_v15", "_v16",
)


@dataclass
class FileRecord:
    path: str
    size_bytes: int
    sha256: str
    module: str | None
    imported_modules: list[str]
    imported_by: list[str]
    is_entry_point: bool
    is_suspect_name: bool
    is_orphan: bool
    duplicate_group: int | None


@dataclass
class DirectoryRecord:
    path: str
    size_bytes: int
    file_count: int


def human_size(value: int) -> str:
    size = float(value)
    for unit in ("o", "Ko", "Mo", "Go", "To"):
        if size < 1024 or unit == "To":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} To"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_project_files(root: Path):
    for current_root, dir_names, file_names in os.walk(root):
        current_path = Path(current_root)
        dir_names[:] = [name for name in dir_names if name not in IGNORE_DIRS]
        for file_name in file_names:
            yield current_path / file_name


def python_files(root: Path) -> list[Path]:
    return sorted(path for path in iter_project_files(root) if path.suffix.lower() == ".py")


def relative(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def path_to_module(path: Path) -> str | None:
    try:
        rel = path.relative_to(PROJECT_ROOT)
    except ValueError:
        return None
    if rel.suffix != ".py":
        return None
    parts = list(rel.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) if parts else None


def parse_imports(path: Path) -> set[str]:
    imports: set[str] = set()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except Exception:
        return imports
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imports.add(node.module)
    return imports


def resolve_local_module(imported_module: str, module_to_file: dict[str, Path]) -> str | None:
    candidate = imported_module
    while candidate:
        if candidate in module_to_file:
            return candidate
        if "." not in candidate:
            break
        candidate = candidate.rsplit(".", 1)[0]
    return None


def build_dependency_graph(files: list[Path]):
    module_to_file = {
        module: path
        for path in files
        if (module := path_to_module(path)) is not None
    }
    imports_by_module: dict[str, set[str]] = defaultdict(set)
    imported_by_module: dict[str, set[str]] = defaultdict(set)
    for path in files:
        source_module = path_to_module(path)
        if source_module is None:
            continue
        for imported in parse_imports(path):
            local_module = resolve_local_module(imported, module_to_file)
            if local_module is None:
                continue
            imports_by_module[source_module].add(local_module)
            imported_by_module[local_module].add(source_module)
    return module_to_file, imports_by_module, imported_by_module


def reachable_modules(module_to_file: dict[str, Path], imports_by_module: dict[str, set[str]]) -> set[str]:
    starts: set[str] = set()
    for entry in ENTRY_POINTS:
        path = PROJECT_ROOT / entry
        if path.exists() and (module := path_to_module(path)):
            starts.add(module)
    for module, path in module_to_file.items():
        if relative(path).startswith("tools/"):
            starts.add(module)
    reachable: set[str] = set()
    queue = deque(starts)
    while queue:
        module = queue.popleft()
        if module in reachable:
            continue
        reachable.add(module)
        queue.extend(dep for dep in imports_by_module.get(module, set()) if dep not in reachable)
    return reachable


def suspect_name(path: Path) -> bool:
    stem = path.stem.lower()
    return stem.startswith("test_") or stem.endswith("_test") or any(p in stem for p in SUSPECT_PATTERNS)


def duplicate_groups(files: list[Path]):
    by_hash: dict[str, list[Path]] = defaultdict(list)
    for path in files:
        try:
            by_hash[sha256_file(path)].append(path)
        except OSError:
            pass
    groups: dict[Path, int] = {}
    group_id = 1
    for paths in by_hash.values():
        if len(paths) < 2:
            continue
        for path in paths:
            groups[path] = group_id
        group_id += 1
    return groups


def directory_size(path: Path) -> tuple[int, int]:
    total = 0
    count = 0
    if not path.exists():
        return total, count
    for file_path in path.rglob("*"):
        if file_path.is_file():
            try:
                total += file_path.stat().st_size
                count += 1
            except OSError:
                pass
    return total, count


def generated_directories(root: Path) -> list[DirectoryRecord]:
    records: list[DirectoryRecord] = []
    for path in root.rglob("*"):
        if path.is_dir() and path.name.lower() in GENERATED_DIR_NAMES:
            if any(part in IGNORE_DIRS for part in path.parts):
                continue
            size, count = directory_size(path)
            records.append(DirectoryRecord(relative(path), size, count))
    return sorted(records, key=lambda item: item.size_bytes, reverse=True)


def create_file_records() -> list[FileRecord]:
    files = python_files(PROJECT_ROOT)
    module_to_file, imports_by_module, imported_by_module = build_dependency_graph(files)
    reachable = reachable_modules(module_to_file, imports_by_module)
    duplicates = duplicate_groups(files)
    records: list[FileRecord] = []
    for path in files:
        module = path_to_module(path)
        rel = relative(path)
        records.append(FileRecord(
            path=rel,
            size_bytes=path.stat().st_size,
            sha256=sha256_file(path),
            module=module,
            imported_modules=sorted(imports_by_module.get(module or "", set())),
            imported_by=sorted(imported_by_module.get(module or "", set())),
            is_entry_point=rel in ENTRY_POINTS,
            is_suspect_name=suspect_name(path),
            is_orphan=bool(module and module not in reachable and not rel.startswith("tests/")),
            duplicate_group=duplicates.get(path),
        ))
    return records


def write_reports(file_records: list[FileRecord], directory_records: list[DirectoryRecord]):
    report_dir = PROJECT_ROOT / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_file = report_dir / f"audit_v5_{stamp}.json"
    text_file = report_dir / f"audit_v5_{stamp}.txt"
    payload = {
        "project_root": str(PROJECT_ROOT),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "files": [asdict(item) for item in file_records],
        "generated_directories": [asdict(item) for item in directory_records],
    }
    json_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    suspects = [item for item in file_records if item.is_suspect_name]
    orphans = [item for item in file_records if item.is_orphan]
    duplicates: dict[int, list[FileRecord]] = defaultdict(list)
    for item in file_records:
        if item.duplicate_group is not None:
            duplicates[item.duplicate_group].append(item)

    lines = [
        "=" * 72,
        "GPX FLYOVER STUDIO V5 - AUDIT",
        "=" * 72,
        "",
        f"Racine : {PROJECT_ROOT}",
        f"Fichiers Python : {len(file_records)}",
        f"Noms suspects : {len(suspects)}",
        f"Modules orphelins potentiels : {len(orphans)}",
        f"Groupes de doublons exacts : {len(duplicates)}",
        "",
        "DOSSIERS GÉNÉRÉS",
        "-" * 72,
    ]
    lines.extend(
        f"{item.path:<45} {human_size(item.size_bytes):>12} {item.file_count:>8} fichiers"
        for item in directory_records
    )
    if not directory_records:
        lines.append("Aucun.")

    lines += ["", "FICHIERS AUX NOMS SUSPECTS", "-" * 72]
    lines.extend(item.path for item in suspects) if suspects else lines.append("Aucun.")

    lines += ["", "MODULES ORPHELINS POTENTIELS", "-" * 72]
    lines.extend(item.path for item in orphans) if orphans else lines.append("Aucun.")

    lines += ["", "DOUBLONS EXACTS", "-" * 72]
    if duplicates:
        for group_id, items in sorted(duplicates.items()):
            lines.append(f"Groupe {group_id}")
            lines.extend(f"  - {item.path}" for item in items)
    else:
        lines.append("Aucun.")

    lines += ["", "Aucune suppression effectuée.", ""]
    text_file.write_text("\n".join(lines), encoding="utf-8")
    return text_file, json_file


def archive_candidates(file_records: list[FileRecord], include_orphans: bool):
    candidates: set[str] = set()
    for item in file_records:
        if item.is_entry_point or item.path.startswith("tools/"):
            continue
        if item.is_suspect_name or (include_orphans and item.is_orphan):
            candidates.add(item.path)

    grouped: dict[int, list[FileRecord]] = defaultdict(list)
    for item in file_records:
        if item.duplicate_group is not None:
            grouped[item.duplicate_group].append(item)
    for items in grouped.values():
        ordered = sorted(items, key=lambda item: (item.is_suspect_name, item.path.count("/"), len(item.path)))
        for item in ordered[1:]:
            candidates.add(item.path)
    return sorted(candidates)


def archive_files(candidates: list[str], dry_run: bool):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_root = PROJECT_ROOT / "_archive" / stamp
    manifest = {"created_at": datetime.now().isoformat(timespec="seconds"), "files": []}
    for rel_path in candidates:
        source = PROJECT_ROOT / rel_path
        if not source.is_file():
            continue
        destination = archive_root / rel_path
        print("[SIMULATION]" if dry_run else "[ARCHIVE]", rel_path)
        manifest["files"].append({"source": rel_path, "destination": relative(destination)})
        if not dry_run:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
    if dry_run:
        return None
    archive_root.mkdir(parents=True, exist_ok=True)
    (archive_root / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return archive_root


def clean_generated_directories(directory_records: list[DirectoryRecord], dry_run: bool):
    for item in directory_records:
        path = PROJECT_ROOT / item.path
        print("[SIMULATION]" if dry_run else "[NETTOYAGE]", item.path, human_size(item.size_bytes))
        if not dry_run and path.exists():
            shutil.rmtree(path)


def purge_archives(dry_run: bool):
    archive_root = PROJECT_ROOT / "_archive"
    if not archive_root.exists():
        print("Aucune archive.")
        return
    print("[SIMULATION]" if dry_run else "[SUPPRESSION]", relative(archive_root))
    if not dry_run:
        shutil.rmtree(archive_root)


def parse_arguments():
    parser = argparse.ArgumentParser(description="Audit et nettoyage sécurisé de GPX Flyover Studio V5.")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--archive", action="store_true")
    parser.add_argument("--include-orphans", action="store_true")
    parser.add_argument("--clean-generated", action="store_true")
    parser.add_argument("--purge", action="store_true")
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main():
    args = parse_arguments()
    if not any((args.audit, args.archive, args.clean_generated, args.purge)):
        args.audit = True

    print("=" * 72)
    print("GPX FLYOVER STUDIO V5 - CLEANUP")
    print("=" * 72)
    print("Racine :", PROJECT_ROOT)
    print()

    file_records = create_file_records()
    directory_records = generated_directories(PROJECT_ROOT)
    text_report, json_report = write_reports(file_records, directory_records)
    print("Rapport TXT  :", text_report)
    print("Rapport JSON :", json_report)

    dry_run = not args.apply
    if args.archive:
        candidates = archive_candidates(file_records, args.include_orphans)
        print("\nCandidats à l'archivage :", len(candidates))
        archive_root = archive_files(candidates, dry_run)
        if archive_root is not None:
            print("Archive créée :", archive_root)
    if args.clean_generated:
        print()
        clean_generated_directories(directory_records, dry_run)
    if args.purge:
        print()
        purge_archives(dry_run)
    if dry_run and any((args.archive, args.clean_generated, args.purge)):
        print("\nSimulation uniquement. Ajoute --apply pour appliquer.")


if __name__ == "__main__":
    main()
