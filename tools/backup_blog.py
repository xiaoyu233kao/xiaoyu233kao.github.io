"""Snapshot the local website to a private GitHub release; restore without overwriting."""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import subprocess
import sys
from datetime import datetime, timedelta, timezone
import zipfile

DEFAULT_REPO = "xiaoyu233kao/blog-site-backup"
EXCLUDED = {"素材与历史"}
HK = timezone(timedelta(hours=8))


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def gh(arguments, proxy=None, payload=None):
    environment = os.environ.copy()
    if proxy:
        environment.update(HTTPS_PROXY=proxy, HTTP_PROXY=proxy)
    result = subprocess.run(
        ["gh", *arguments], env=environment, capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False,
        input=json.dumps(payload, ensure_ascii=False) if payload is not None else None,
    )
    if result.returncode:
        raise RuntimeError(f"GitHub command failed: {result.stderr.strip()}")
    return result.stdout


def sync_private_essays(root, repo, proxy):
    """Mirror private Markdown to the private backup repository, never to Pages."""
    folder = root / "私人随笔"
    if not folder.exists():
        return None
    metadata = json.loads(gh(["api", f"repos/{repo}"], proxy))
    if not metadata["private"]:
        raise RuntimeError("Private essays may only be synced to a private repository")
    if folder.is_symlink() or folder.is_junction():
        raise RuntimeError("Private essay folder must not be a directory link")
    files = sorted(folder.glob("*.md"))
    if not files:
        raise RuntimeError("Private essay folder contains no Markdown files")
    desired = {}
    updates = []
    for path in files:
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"Unexpected private essay entry: {path.name}")
        data = path.read_bytes()
        remote_path = "essays/" + path.name
        digest = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        desired[remote_path] = digest
        updates.append({"path": remote_path, "mode": "100644", "type": "blob",
                        "content": data.decode("utf-8")})
    branch = metadata["default_branch"]
    reference = json.loads(gh(["api", f"repos/{repo}/git/ref/heads/{branch}"], proxy))
    head = reference["object"]["sha"]
    commit = json.loads(gh(["api", f"repos/{repo}/git/commits/{head}"], proxy))
    tree = json.loads(gh(["api", f"repos/{repo}/git/trees/{commit['tree']['sha']}?recursive=1"], proxy))
    if tree.get("truncated"):
        raise RuntimeError("Private repository tree was truncated")
    existing = {item["path"]: item["sha"] for item in tree["tree"]
                if item["type"] == "blob" and item["path"].startswith("essays/")}
    if existing != desired:
        for name in existing.keys() - desired.keys():
            updates.append({"path": name, "mode": "100644", "type": "blob", "sha": None})
        new_tree = json.loads(gh(
            ["api", "--method", "POST", f"repos/{repo}/git/trees", "--input", "-"], proxy,
            {"base_tree": commit["tree"]["sha"], "tree": updates}))
        new_commit = json.loads(gh(
            ["api", "--method", "POST", f"repos/{repo}/git/commits", "--input", "-"], proxy,
            {"message": "Sync private essays", "tree": new_tree["sha"], "parents": [head]}))
        gh(["api", "--method", "PATCH", f"repos/{repo}/git/refs/heads/{branch}", "--input", "-"],
           proxy, {"sha": new_commit["sha"], "force": False})
        head = new_commit["sha"]
        verified_tree = json.loads(gh(
            ["api", f"repos/{repo}/git/trees/{new_tree['sha']}?recursive=1"], proxy))
        actual = {item["path"]: item["sha"] for item in verified_tree["tree"]
                  if item["type"] == "blob" and item["path"].startswith("essays/")}
        if actual != desired:
            raise RuntimeError("Private essay sync verification failed")
    result = {"url": f"https://github.com/{repo}/tree/{branch}/essays",
              "file_count": len(files), "commit": head, "verified": True}
    print(f"Private essay Markdown verified: {len(files)} files", flush=True)
    return result


def walk(root):
    """Never follow junctions or symlinks, including excluded material directories."""
    pending = [root]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            children = sorted(entries, key=lambda entry: entry.name)
        for entry in children:
            path = Path(entry.path)
            relative = path.relative_to(root)
            if relative.parts[0] in EXCLUDED:
                continue
            info = entry.stat(follow_symlinks=False)
            if getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
                yield path, relative.as_posix(), "link", info
            elif entry.is_dir(follow_symlinks=False):
                yield path, relative.as_posix(), "directory", info
                pending.append(path)
            elif entry.is_file(follow_symlinks=False):
                yield path, relative.as_posix(), "file", info
            else:
                raise RuntimeError(f"Unsupported filesystem entry: {path}")


def validate_relative(value):
    relative = PurePosixPath(value)
    if (relative.is_absolute() or ".." in relative.parts or "\\" in value
            or ":" in value or not relative.parts):
        raise RuntimeError(f"Unsafe archive path: {value}")
    return relative


def verify_archive(archive):
    with zipfile.ZipFile(archive) as zipped:
        manifest = json.loads(zipped.read("snapshot-manifest.json"))
        names = zipped.namelist()
        expected = {"snapshot-manifest.json"}
        for record in manifest["entries"]:
            validate_relative(record["path"])
            if record["kind"] != "file":
                continue
            member = "blog-site/" + record["path"]
            if member in expected:
                raise RuntimeError(f"Duplicate manifest entry: {member}")
            expected.add(member)
            info = zipped.getinfo(member)
            with zipped.open(member) as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            if digest != record["sha256"] or info.file_size != record["bytes"]:
                raise RuntimeError(f"Archive verification failed: {record['path']}")
        if len(names) != len(expected) or set(names) != expected:
            raise RuntimeError("Archive members differ from the manifest")
    return manifest


def create_archive(root, output):
    root = root.resolve(strict=True)
    output = output.resolve()
    if output.is_relative_to(root):
        raise RuntimeError("Backup output must be outside the source tree")
    output.mkdir(parents=True, exist_ok=False)
    timestamp = datetime.now(HK).strftime("%Y%m%d-%H%M%S-%f")
    archive = output / f"blog-site-{timestamp}.zip"
    manifest = {
        "format": 1,
        "created_at": datetime.now(HK).isoformat(),
        "source_root": str(root),
        "excluded_top_level": sorted(EXCLUDED),
        "entries": [],
    }
    file_count = 0
    total_bytes = 0
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=3, allowZip64=True) as zipped:
        for path, relative, kind, info in walk(root):
            record = {"path": relative, "kind": kind}
            if kind == "link":
                record.update(
                    target=os.readlink(path),
                    directory=bool(info.st_file_attributes & stat.FILE_ATTRIBUTE_DIRECTORY),
                )
            elif kind == "file":
                record.update(bytes=info.st_size, mtime_ns=info.st_mtime_ns,
                              mode=stat.S_IMODE(info.st_mode))
                zipped_info = zipfile.ZipInfo("blog-site/" + relative)
                zipped_info.compress_type = zipfile.ZIP_DEFLATED
                zipped_info.external_attr = info.st_mode << 16
                digest = hashlib.sha256()
                with path.open("rb") as source, zipped.open(zipped_info, "w", force_zip64=True) as target:
                    while block := source.read(1024 * 1024):
                        digest.update(block)
                        target.write(block)
                after = path.stat()
                if after.st_size != info.st_size or after.st_mtime_ns != info.st_mtime_ns:
                    raise RuntimeError(f"File changed while backing up; retry: {relative}")
                record["sha256"] = digest.hexdigest()
                file_count += 1
                total_bytes += info.st_size
                if file_count % 2000 == 0:
                    print(f"Archived {file_count} files", flush=True)
            manifest["entries"].append(record)
        manifest.update(file_count=file_count, total_bytes=total_bytes)
        zipped.writestr("snapshot-manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    verify_archive(archive)
    digest = sha256(archive)
    checksum = archive.with_suffix(".zip.sha256")
    checksum.write_text(f"{digest}  {archive.name}\n", encoding="utf-8")
    print(f"Verified archive: {file_count} files, {total_bytes} bytes", flush=True)
    return archive, checksum, manifest, digest


def publish(archive, checksum, manifest, digest, repo, proxy):
    metadata = json.loads(gh(["api", f"repos/{repo}"], proxy))
    if not metadata["private"]:
        raise RuntimeError("Full local snapshots must be stored in a private repository")
    tag = archive.stem
    notes = (f"Verified snapshot of D:\\blog-site. Files: {manifest['file_count']}; "
             f"uncompressed bytes: {manifest['total_bytes']}. "
             "Excluded: 素材与历史. canon and 菲林 remain outside this project root. "
             f"SHA256: {digest}")
    gh(["release", "create", tag, str(archive), str(checksum), "--repo", repo,
        "--target", metadata["default_branch"], "--draft", "--title", tag, "--notes", notes], proxy)
    return verify_release(archive, manifest, digest, repo, proxy)


def verify_release(archive, manifest, digest, repo, proxy):
    metadata = json.loads(gh(["api", f"repos/{repo}"], proxy))
    if not metadata["private"]:
        raise RuntimeError("Full local snapshots must be stored in a private repository")
    tag = archive.stem
    # The REST tag endpoint does not expose unpublished draft releases.
    release = json.loads(gh(["release", "view", tag, "--repo", repo,
                             "--json", "assets,isDraft"], proxy))
    asset = next(item for item in release["assets"] if item["name"] == archive.name)
    if asset["size"] != archive.stat().st_size:
        raise RuntimeError("Remote asset size mismatch; release left as draft")
    if asset.get("digest") and asset["digest"] != "sha256:" + digest:
        raise RuntimeError("Remote asset digest mismatch; release left as draft")
    download = archive.parent / "remote-verification"
    download.mkdir(exist_ok=True)
    gh(["release", "download", tag, "--repo", repo, "--pattern", archive.name,
        "--dir", str(download), "--clobber"], proxy)
    downloaded = download / archive.name
    if sha256(downloaded) != digest:
        raise RuntimeError("Remote archive SHA256 mismatch; release left as draft")
    verify_archive(downloaded)
    if release["isDraft"]:
        gh(["release", "edit", tag, "--repo", repo, "--draft=false"], proxy)
    print("Remote archive downloaded and verified", flush=True)
    return f"https://github.com/{repo}/releases/tag/{tag}"


def restore(archive, destination):
    destination = destination.resolve()
    if destination.exists() and any(destination.iterdir()):
        raise RuntimeError("Restore destination must be new or empty")
    manifest = verify_archive(archive)
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zipped:
        for record in manifest["entries"]:
            relative = validate_relative(record["path"])
            target = destination.joinpath(*relative.parts)
            if record["kind"] == "directory":
                target.mkdir(parents=True, exist_ok=True)
            elif record["kind"] == "file":
                target.parent.mkdir(parents=True, exist_ok=True)
                with zipped.open("blog-site/" + record["path"]) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output)
                if sha256(target) != record["sha256"]:
                    raise RuntimeError(f"Restored file hash mismatch: {target}")
                os.utime(target, ns=(record["mtime_ns"], record["mtime_ns"]))
                os.chmod(target, record["mode"])
    original_root = Path(manifest["source_root"])
    for record in manifest["entries"]:
        if record["kind"] != "link":
            continue
        target_value = record["target"]
        if target_value.startswith("\\\\?\\"):
            target_value = target_value[4:]
        original_target = Path(target_value)
        if original_target.is_absolute() and original_target.is_relative_to(original_root):
            target_value = str(destination / original_target.relative_to(original_root))
        link = destination.joinpath(*validate_relative(record["path"]).parts)
        link.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(target_value, link, target_is_directory=record["directory"])
    print(f"Restored and verified {manifest['file_count']} files to {destination}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    backup_parser = subparsers.add_parser("backup")
    backup_parser.add_argument("--root", type=Path, default=Path(r"D:\blog-site"))
    backup_parser.add_argument("--output", type=Path, default=Path(r"D:\codex\blog-backup"))
    backup_parser.add_argument("--repo", default=DEFAULT_REPO)
    backup_parser.add_argument("--proxy", default="http://127.0.0.1:7890")
    backup_parser.add_argument("--offline", action="store_true")
    sync_parser = subparsers.add_parser("sync-essays", help="Sync private Markdown for signed-in reading")
    sync_parser.add_argument("--root", type=Path, default=Path(r"D:\blog-site"))
    sync_parser.add_argument("--repo", default=DEFAULT_REPO)
    sync_parser.add_argument("--proxy", default="http://127.0.0.1:7890")
    resume_parser = subparsers.add_parser("resume", help="Verify an already uploaded draft snapshot")
    resume_parser.add_argument("archive", type=Path)
    resume_parser.add_argument("--output", type=Path, default=Path(r"D:\codex\blog-backup"))
    resume_parser.add_argument("--repo", default=DEFAULT_REPO)
    resume_parser.add_argument("--proxy", default="http://127.0.0.1:7890")
    restore_parser = subparsers.add_parser("restore")
    restore_parser.add_argument("archive", type=Path)
    restore_parser.add_argument("destination", type=Path)
    arguments = parser.parse_args()
    if arguments.command == "restore":
        restore(arguments.archive, arguments.destination)
        return
    if arguments.command == "sync-essays":
        print(json.dumps(sync_private_essays(arguments.root, arguments.repo, arguments.proxy),
                         ensure_ascii=False, indent=2))
        return
    private_essays = None
    if arguments.command == "resume":
        archive = arguments.archive
        manifest = verify_archive(archive)
        digest = sha256(archive)
        release = verify_release(archive, manifest, digest, arguments.repo, arguments.proxy)
    else:
        if not arguments.offline:
            private_essays = sync_private_essays(arguments.root, arguments.repo, arguments.proxy)
        stamp = datetime.now(HK).strftime("%Y%m%d-%H%M%S-%f")
        archive, checksum, manifest, digest = create_archive(arguments.root, arguments.output / stamp)
        release = None
        if not arguments.offline:
            release = publish(archive, checksum, manifest, digest, arguments.repo, arguments.proxy)
    result = {
        "archive": str(archive), "sha256": digest, "file_count": manifest["file_count"],
        "total_bytes": manifest["total_bytes"], "release": release,
        "remote_verified": bool(release), "created_at": manifest["created_at"],
        "private_essays": private_essays,
    }
    (archive.parent / "backup-result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (arguments.output / "latest-result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Backup failed: {error}", file=sys.stderr)
        sys.exit(1)
