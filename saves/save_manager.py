#!/usr/bin/env python3
"""
TRPG standard archive manager.

Usage examples:
  python saves/save_manager.py status
  python saves/save_manager.py archive -c zhaoyutong --main-roles "赵雨桐+林立" --ai-blip "隧道潜行" --note "Day1 tunnel checkpoint"
  python saves/save_manager.py list
  python saves/save_manager.py restore -c zhaoyutong --snapshot 20260227_160000
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

SCHEMA_VERSION = 1
DEFAULT_ROLE_LIMIT = 3
DEAD_SUFFIX = "_已死亡"
EXCLUDED_ROLE_PREFIXES = ("示例角色",)

RUNTIME_SCOPES: Sequence[Tuple[str, str]] = (
    ("characters", "characters/active/*.md"),
    ("session_logs", "logs/session/*.md"),
    ("combat_logs", "logs/combat/*.md"),
    ("exploration_logs", "logs/exploration/*.md"),
    ("system_logs", "logs/system/*.md"),
    ("saves", "saves/save_*.md"),
)

EXCLUDED_BASENAMES_LOWER = {
    "save_initial_template.md",
    "save_manager.md",
    "save_manager.py",
}
INVALID_WIN_CHARS = re.compile(r'[\\/:*?"<>|]')


@dataclass
class RuntimeFile:
    path: Path
    relative: str
    scope: str


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def archives_root(root: Path) -> Path:
    return root / "saves" / "archives"


def index_path(root: Path) -> Path:
    return archives_root(root) / "index.json"


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def default_snapshot_id() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def normalize_campaign_id(value: str) -> str:
    text = re.sub(r"\s+", "_", value.strip())
    text = INVALID_WIN_CHARS.sub("", text).strip("._")
    if not text:
        raise ValueError("campaign id is empty after normalization")
    return text


def normalize_snapshot_id(value: Optional[str]) -> str:
    if not value:
        return default_snapshot_id()
    text = INVALID_WIN_CHARS.sub("_", value.strip())
    text = re.sub(r"[^0-9A-Za-z_-]", "_", text).strip("._")
    if not text:
        raise ValueError("snapshot id is empty after normalization")
    return text


def normalize_ai_blip(value: str) -> str:
    text = re.sub(r"\s+", " ", (value or "").strip())
    return text[:20]


def normalize_filename_piece(value: str, fallback: str) -> str:
    text = INVALID_WIN_CHARS.sub("", (value or "").strip())
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^\w\u4e00-\u9fff+\-]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("._")
    if not text:
        return fallback
    return text[:32]


def parse_roles_input(value: str) -> List[str]:
    parts = re.split(r"[+,，、/;；\s]+", value.strip())
    result: List[str] = []
    for part in parts:
        name = part.strip()
        if not name or name in result:
            continue
        result.append(name)
    return result


def canonical_character_name(stem: str) -> str:
    name = stem.strip()
    if name.endswith(DEAD_SUFFIX):
        name = name[: -len(DEAD_SUFFIX)].strip()
    return name or stem.strip()


def detect_main_roles(root: Path, limit: int = DEFAULT_ROLE_LIMIT) -> List[str]:
    active_dir = root / "characters" / "active"
    if not active_dir.exists():
        return []
    files = [p for p in active_dir.glob("*.md") if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    names: List[str] = []
    for path in files:
        if path.stem.endswith(DEAD_SUFFIX):
            continue
        if any(path.stem.startswith(prefix) for prefix in EXCLUDED_ROLE_PREFIXES):
            continue
        name = canonical_character_name(path.stem)
        if not name or name in names:
            continue
        names.append(name)
        if len(names) >= limit:
            break
    return names


def resolve_main_roles(root: Path, explicit_roles: str, limit: int = DEFAULT_ROLE_LIMIT) -> List[str]:
    if explicit_roles.strip():
        roles = parse_roles_input(explicit_roles)
        if roles:
            return roles[:limit]
    return detect_main_roles(root, limit=limit)


def build_save_filename_hint(snapshot_id: str, main_roles: Sequence[str], ai_blip: str) -> str:
    roles_label = "+".join(main_roles) if main_roles else "队伍"
    role_part = normalize_filename_piece(roles_label, "队伍")
    if ai_blip:
        blip_part = normalize_filename_piece(ai_blip, "摘要")
        return f"save_{snapshot_id}_{role_part}_{blip_part}.md"
    return f"save_{snapshot_id}_{role_part}.md"


def human_size(size: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    n = float(size)
    for unit in units:
        if n < 1024 or unit == units[-1]:
            return f"{n:.1f}{unit}" if unit != "B" else f"{int(n)}B"
        n /= 1024
    return f"{size}B"


def hash_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def to_posix_relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def safe_relative_path(relative: str) -> Path:
    rel_path = Path(relative)
    if rel_path.is_absolute() or ".." in rel_path.parts:
        raise ValueError(f"invalid relative path in manifest: {relative}")
    return rel_path


def remove_existing_path(path: Path) -> None:
    if not path.exists():
        return
    if path.is_file() or path.is_symlink():
        path.unlink()
        return
    shutil.rmtree(path)


def load_json(path: Path, default: Dict) -> Dict:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"JSON parse failed: {path}") from exc


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def collect_scope_files(root: Path, extra_globs: Optional[Sequence[str]] = None) -> List[RuntimeFile]:
    seen: Dict[str, RuntimeFile] = {}
    for scope, glob_pattern in RUNTIME_SCOPES:
        for path in sorted(root.glob(glob_pattern)):
            if not path.is_file():
                continue
            if path.name.lower() in EXCLUDED_BASENAMES_LOWER:
                continue
            rel = to_posix_relative(root, path)
            if rel.startswith("saves/archives/"):
                continue
            seen.setdefault(rel, RuntimeFile(path=path.resolve(), relative=rel, scope=scope))

    for extra in extra_globs or []:
        pattern = extra.strip()
        if not pattern:
            continue
        for path in sorted(root.glob(pattern)):
            if not path.is_file():
                continue
            rel = to_posix_relative(root, path)
            if rel.startswith("saves/archives/"):
                continue
            seen.setdefault(rel, RuntimeFile(path=path.resolve(), relative=rel, scope="extra"))

    return sorted(seen.values(), key=lambda item: item.relative)


def runtime_scope_summary(files: Sequence[RuntimeFile]) -> Dict[str, int]:
    summary: Dict[str, int] = {}
    for item in files:
        summary[item.scope] = summary.get(item.scope, 0) + 1
    return summary


def build_file_record(path: Path, relative: str, scope: str) -> Dict:
    stat = path.stat()
    mtime = datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds")
    return {
        "relative_path": relative,
        "scope": scope,
        "size_bytes": stat.st_size,
        "mtime": mtime,
        "sha256": hash_sha256(path),
    }


def build_summary_markdown(manifest: Dict) -> str:
    lines: List[str] = [
        f"# 存档封存快照 `{manifest['snapshot_id']}`",
        "",
        "## 元数据",
        f"- 战役ID：`{manifest['campaign_id']}`",
        f"- 快照ID：`{manifest['snapshot_id']}`",
        f"- 创建时间：`{manifest['created_at']}`",
        f"- 封存模式：`{manifest['archive_mode']}`",
        f"- 主角色串：`{manifest.get('main_roles_label') or '队伍'}`",
        f"- AI超简评：`{manifest.get('ai_blip') or '(无)'}`",
        f"- 推荐存档名：`{manifest.get('save_filename_hint') or '(未生成)'}`",
        f"- 文件总数：`{manifest['counts']['files']}`",
        f"- 总大小：`{manifest['counts']['bytes_human']}`",
        "",
        "## 备注",
        manifest.get("note") or "(无)",
        "",
        "## 范围统计",
    ]
    for key, value in manifest.get("scope_counts", {}).items():
        lines.append(f"- `{key}`: {value}")

    lines.extend(["", "## 文件清单", "| 文件 | 大小 |", "|---|---:|"])
    for item in manifest.get("files", []):
        lines.append(f"| `{item['relative_path']}` | {human_size(int(item['size_bytes']))} |")
    lines.append("")
    return "\n".join(lines)


def load_archive_index(root: Path) -> Dict:
    return load_json(index_path(root), {"schema_version": SCHEMA_VERSION, "entries": []})


def update_archive_index(root: Path, entry: Dict) -> None:
    index_data = load_archive_index(root)
    entries = index_data.get("entries", [])
    entries = [
        e
        for e in entries
        if not (
            e.get("campaign_id") == entry.get("campaign_id")
            and e.get("snapshot_id") == entry.get("snapshot_id")
        )
    ]
    entries.append(entry)
    entries.sort(
        key=lambda e: (
            str(e.get("created_at", "")),
            str(e.get("snapshot_id", "")),
        ),
        reverse=True,
    )
    index_data["schema_version"] = SCHEMA_VERSION
    index_data["entries"] = entries
    write_json(index_path(root), index_data)


def read_manifest(path: Path) -> Dict:
    data = load_json(path, {})
    if not data:
        raise RuntimeError(f"manifest is empty: {path}")
    if "files" not in data or "campaign_id" not in data or "snapshot_id" not in data:
        raise RuntimeError(f"manifest schema invalid: {path}")
    return data


def list_manifests(root: Path, campaign: Optional[str] = None) -> List[Tuple[Path, Dict]]:
    archive_dir = archives_root(root)
    if not archive_dir.exists():
        return []

    manifests: List[Tuple[Path, Dict]] = []
    for campaign_dir in sorted(archive_dir.iterdir()):
        if not campaign_dir.is_dir():
            continue
        if campaign and campaign_dir.name != campaign:
            continue
        for snapshot_dir in sorted(campaign_dir.iterdir()):
            manifest_path = snapshot_dir / "manifest.json"
            if not manifest_path.exists():
                continue
            try:
                manifests.append((manifest_path, read_manifest(manifest_path)))
            except RuntimeError:
                continue

    manifests.sort(
        key=lambda row: (
            str(row[1].get("created_at", "")),
            str(row[1].get("snapshot_id", "")),
        ),
        reverse=True,
    )
    return manifests


def resolve_manifest(root: Path, campaign_id: str, snapshot_id: Optional[str]) -> Path:
    campaign_dir = archives_root(root) / campaign_id
    if not campaign_dir.exists():
        raise RuntimeError(f"campaign not found: {campaign_id}")

    if snapshot_id:
        manifest_path = campaign_dir / snapshot_id / "manifest.json"
        if not manifest_path.exists():
            raise RuntimeError(f"snapshot not found: {campaign_id}/{snapshot_id}")
        return manifest_path

    candidates = list_manifests(root, campaign=campaign_id)
    if not candidates:
        raise RuntimeError(f"no snapshots under campaign: {campaign_id}")
    return candidates[0][0]


def cmd_status(args: argparse.Namespace) -> int:
    root = project_root()
    files = collect_scope_files(root, extra_globs=args.extra)
    by_scope = runtime_scope_summary(files)
    total_bytes = sum(item.path.stat().st_size for item in files)

    print("== Runtime Status ==")
    print(f"project_root: {root}")
    print(f"runtime_files: {len(files)}")
    print(f"runtime_bytes: {human_size(total_bytes)}")
    print("")
    print("scope_counts:")
    for scope, _ in RUNTIME_SCOPES:
        print(f"  - {scope}: {by_scope.get(scope, 0)}")
    if args.extra:
        print(f"  - extra: {by_scope.get('extra', 0)}")
    print("")
    print("new_game_ready:", "yes" if len(files) == 0 else "no")

    if args.verbose and files:
        print("")
        print("files:")
        for item in files:
            print(f"  - {item.relative}")
    return 0


def cmd_archive(args: argparse.Namespace) -> int:
    root = project_root()
    campaign_id = normalize_campaign_id(args.campaign)
    snapshot_id = normalize_snapshot_id(args.snapshot)
    role_limit = max(1, int(args.role_limit))

    files = collect_scope_files(root, extra_globs=args.extra)
    if not files:
        print("没有可封存的运行态文件，终止。")
        return 1

    main_roles = resolve_main_roles(root, args.main_roles, limit=role_limit)
    main_roles_label = "+".join(main_roles) if main_roles else "队伍"
    ai_blip = normalize_ai_blip(args.ai_blip)
    save_filename_hint = build_save_filename_hint(snapshot_id, main_roles, ai_blip)

    snapshot_dir = archives_root(root) / campaign_id / snapshot_id
    data_dir = snapshot_dir / "data"
    manifest_file = snapshot_dir / "manifest.json"
    summary_file = snapshot_dir / "summary.md"

    if snapshot_dir.exists():
        print(f"目标快照已存在：{snapshot_dir}")
        return 1

    total_size = sum(item.path.stat().st_size for item in files)
    if args.dry_run:
        print("== Archive Dry Run ==")
    else:
        print("== Archive ==")
    print(f"campaign: {campaign_id}")
    print(f"snapshot: {snapshot_id}")
    print(f"mode: {args.mode}")
    print(f"main_roles: {main_roles_label}")
    if ai_blip:
        print(f"ai_blip: {ai_blip}")
    print(f"save_filename_hint: {save_filename_hint}")
    print(f"files: {len(files)} ({human_size(total_size)})")
    if args.note:
        print(f"note: {args.note}")

    records: List[Dict] = []
    moved_count = 0

    if not args.dry_run:
        data_dir.mkdir(parents=True, exist_ok=False)

    for item in files:
        source = item.path
        relative_path = item.relative
        destination = data_dir / safe_relative_path(relative_path)

        if args.dry_run:
            records.append(build_file_record(source, relative_path, item.scope))
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        if args.mode == "move":
            shutil.move(str(source), str(destination))
            moved_count += 1
        else:
            shutil.copy2(str(source), str(destination))
        records.append(build_file_record(destination, relative_path, item.scope))

    created_at = now_iso()
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "type": "trpg_runtime_archive",
        "campaign_id": campaign_id,
        "snapshot_id": snapshot_id,
        "created_at": created_at,
        "archive_mode": args.mode,
        "main_roles": list(main_roles),
        "main_roles_label": main_roles_label,
        "ai_blip": ai_blip,
        "save_filename_hint": save_filename_hint,
        "note": args.note or "",
        "source_root": str(root),
        "scope_counts": runtime_scope_summary(files),
        "counts": {
            "files": len(records),
            "bytes": sum(int(item["size_bytes"]) for item in records),
            "bytes_human": human_size(sum(int(item["size_bytes"]) for item in records)),
        },
        "files": records,
    }

    if args.dry_run:
        print("dry-run complete, no files changed.")
        return 0

    write_json(manifest_file, manifest)
    summary_file.write_text(build_summary_markdown(manifest), encoding="utf-8")

    update_archive_index(
        root,
        {
            "campaign_id": campaign_id,
            "snapshot_id": snapshot_id,
            "created_at": created_at,
            "archive_mode": args.mode,
            "main_roles_label": main_roles_label,
            "ai_blip": ai_blip,
            "save_filename_hint": save_filename_hint,
            "file_count": manifest["counts"]["files"],
            "total_bytes": manifest["counts"]["bytes"],
            "note": args.note or "",
        },
    )

    print(f"archived: {manifest['counts']['files']} files")
    print(f"archive_path: {snapshot_dir}")
    if args.mode == "move":
        print(f"migrated_out_of_runtime: {moved_count}")
    print("written: manifest.json, summary.md")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    root = project_root()
    campaign = normalize_campaign_id(args.campaign) if args.campaign else None
    manifests = list_manifests(root, campaign=campaign)

    if not manifests:
        print("没有已封存快照。")
        return 0

    print("== Archive Snapshots ==")
    for _, manifest in manifests:
        count = manifest.get("counts", {}).get("files", 0)
        size = manifest.get("counts", {}).get("bytes", 0)
        note = manifest.get("note") or "-"
        roles = manifest.get("main_roles_label") or "队伍"
        blip = manifest.get("ai_blip") or "-"
        print(
            f"- {manifest.get('campaign_id')}/{manifest.get('snapshot_id')} "
            f"| {manifest.get('created_at')} | roles={roles} | blip={blip} "
            f"| files={count} | size={human_size(int(size))} | note={note}"
        )
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    root = project_root()
    campaign_id = normalize_campaign_id(args.campaign)
    snapshot_id = normalize_snapshot_id(args.snapshot) if args.snapshot else None

    manifest_path = resolve_manifest(root, campaign_id, snapshot_id)
    manifest = read_manifest(manifest_path)
    snapshot_dir = manifest_path.parent
    data_dir = snapshot_dir / "data"
    if not data_dir.exists():
        raise RuntimeError(f"archive data directory not found: {data_dir}")

    records: List[Dict] = list(manifest.get("files", []))
    if not records:
        print("目标快照文件为空，无需恢复。")
        return 0

    collisions: List[str] = []
    missing_sources: List[str] = []
    restore_plan: List[Tuple[Path, Path, Dict]] = []

    for record in records:
        relative = str(record.get("relative_path", "")).strip()
        rel_path = safe_relative_path(relative)
        source = data_dir / rel_path
        target = root / rel_path
        restore_plan.append((source, target, record))

        if not source.exists():
            missing_sources.append(relative)
        if target.exists():
            collisions.append(relative)

    if missing_sources:
        print("恢复失败：快照内缺少以下文件：")
        for item in missing_sources[:20]:
            print(f"  - {item}")
        if len(missing_sources) > 20:
            print(f"  ... and {len(missing_sources) - 20} more")
        return 1

    if collisions and not args.force:
        print("恢复终止：目标路径已有文件。")
        print("请先封存当前局，或改用 --force 覆盖。冲突文件：")
        for item in collisions[:20]:
            print(f"  - {item}")
        if len(collisions) > 20:
            print(f"  ... and {len(collisions) - 20} more")
        return 1

    mode = "move" if args.move_from_archive else "copy"
    if args.dry_run:
        print("== Restore Dry Run ==")
    else:
        print("== Restore ==")
    print(f"campaign: {manifest.get('campaign_id')}")
    print(f"snapshot: {manifest.get('snapshot_id')}")
    print(f"mode: {mode}")
    print(f"files: {len(restore_plan)}")
    if collisions:
        print(f"overwrites: {len(collisions)} (via --force)")

    restored = 0
    for source, target, record in restore_plan:
        if args.dry_run:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if args.force and target.exists():
            remove_existing_path(target)

        if args.move_from_archive:
            shutil.move(str(source), str(target))
        else:
            shutil.copy2(str(source), str(target))

        if not args.skip_hash_check:
            expected_hash = str(record.get("sha256", "")).strip()
            if expected_hash:
                current_hash = hash_sha256(target)
                if current_hash != expected_hash:
                    raise RuntimeError(f"hash mismatch: {record.get('relative_path')}")
        restored += 1

    if args.dry_run:
        print("dry-run complete, no files changed.")
        return 0

    print(f"restored: {restored} files")
    print(f"from: {snapshot_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="TRPG 存档标准管理器：封存当前局并可按快照恢复。"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_status = sub.add_parser("status", help="查看当前运行态文件状态")
    p_status.add_argument(
        "--extra",
        action="append",
        default=[],
        help="额外统计的 glob 路径（相对项目根）",
    )
    p_status.add_argument("--verbose", action="store_true", help="显示文件清单")
    p_status.set_defaults(func=cmd_status)

    p_archive = sub.add_parser("archive", help="封存当前运行态文件")
    p_archive.add_argument("-c", "--campaign", required=True, help="战役ID（例如 zhaoyutong）")
    p_archive.add_argument("--snapshot", help="自定义快照ID，默认 YYYYMMDD_HHMMSS")
    p_archive.add_argument(
        "--main-roles",
        default="",
        help="主角色名，使用 + 或逗号分隔；留空则自动从 characters/active 推断",
    )
    p_archive.add_argument(
        "--role-limit",
        type=int,
        default=DEFAULT_ROLE_LIMIT,
        help=f"自动推断主角色时最多取前N个（默认 {DEFAULT_ROLE_LIMIT}）",
    )
    p_archive.add_argument(
        "--ai-blip",
        default="",
        help="AI超简评（建议<=20字），会写入manifest并用于推荐存档名",
    )
    p_archive.add_argument(
        "--mode",
        choices=["move", "copy"],
        default="move",
        help="move=迁移并清空当前局，copy=仅复制",
    )
    p_archive.add_argument("--note", default="", help="封存备注")
    p_archive.add_argument(
        "--extra",
        action="append",
        default=[],
        help="额外纳入封存的 glob 路径（相对项目根）",
    )
    p_archive.add_argument("--dry-run", action="store_true", help="仅预览，不写入")
    p_archive.set_defaults(func=cmd_archive)

    p_list = sub.add_parser("list", help="列出封存快照")
    p_list.add_argument("-c", "--campaign", help="仅显示指定战役ID")
    p_list.set_defaults(func=cmd_list)

    p_restore = sub.add_parser("restore", help="从快照恢复到运行目录")
    p_restore.add_argument("-c", "--campaign", required=True, help="战役ID")
    p_restore.add_argument(
        "--snapshot",
        help="快照ID；留空则恢复该战役最新快照",
    )
    p_restore.add_argument("--force", action="store_true", help="覆盖目标已有文件")
    p_restore.add_argument(
        "--move-from-archive",
        action="store_true",
        help="将快照内文件移动回运行目录（默认是复制）",
    )
    p_restore.add_argument(
        "--skip-hash-check",
        action="store_true",
        help="跳过恢复后 hash 校验（默认校验）",
    )
    p_restore.add_argument("--dry-run", action="store_true", help="仅预览，不写入")
    p_restore.set_defaults(func=cmd_restore)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
