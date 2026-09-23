"""Validate, commit and push stable local edits. Runtime state stays inside .git."""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
REMOTE = "https://github.com/womengjianhai/CTBench_leaderboard.git"
REPOSITORY = "womengjianhai/CTBench_leaderboard"
PYTHON = str(Path(sys.executable).with_name("python.exe")) if os.name == "nt" else sys.executable
LOG = logging.getLogger("ctbench-sync")


class Sync:
    def __init__(self, root=ROOT, remote=REMOTE, validate=True):
        self.root = Path(root)
        self.remote = remote
        self.validate = validate
        self.env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="Never")

    def run(self, args, check=True):
        result = subprocess.run(
            args, cwd=self.root, env=self.env, capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=180,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        if check and result.returncode:
            raise RuntimeError(f"{args[0]} failed: {(result.stderr or result.stdout)[-2000:].strip()}")
        return result

    def git(self, *args, check=True):
        return self.run(["git", *args], check=check)

    def fingerprint(self):
        digest = hashlib.sha256()
        names = self.git("ls-files", "-z", "--cached", "--others", "--exclude-standard").stdout
        for name in sorted(set(names.split("\0")) - {""}):
            path = self.root / name
            try:
                info = path.stat()
            except FileNotFoundError:
                continue
            digest.update(name.encode("utf-8"))
            digest.update(f"{info.st_size}:{info.st_mtime_ns}".encode())
        return digest.hexdigest()

    def guard(self):
        if self.git("branch", "--show-current").stdout.strip() != "main":
            raise RuntimeError("Auto-sync requires branch main; return to main to resume.")
        if self.git("remote", "get-url", "--push", "origin").stdout.strip() != self.remote:
            raise RuntimeError("origin no longer matches the configured GitHub repository.")
        for marker in ("MERGE_HEAD", "CHERRY_PICK_HEAD", "REVERT_HEAD", "rebase-merge", "rebase-apply", "index.lock"):
            path = Path(self.git("rev-parse", "--git-path", marker).stdout.strip())
            if not path.is_absolute():
                path = self.root / path
            if path.exists():
                raise RuntimeError("A Git operation is in progress; auto-sync will retry later.")
        if self.git("diff", "--name-only", "--diff-filter=U").stdout.strip():
            raise RuntimeError("Resolve merge conflicts before auto-sync can continue.")

    def sync(self):
        self.guard()
        self.git("fetch", "--quiet", "origin", "main")
        if self.git("merge-base", "--is-ancestor", "origin/main", "HEAD", check=False).returncode:
            raise RuntimeError("Remote main has new commits. Pause auto-sync and reconcile them locally before resuming.")
        changed = bool(self.git("status", "--porcelain").stdout)
        ahead = int(self.git("rev-list", "--count", "origin/main..HEAD").stdout.strip())
        if not changed and not ahead:
            return "up-to-date"
        before = self.fingerprint()
        if self.validate:
            self.run([PYTHON, "-m", "unittest", "discover", "-s", "tests", "-p", "test_site_build.py", "-v"])
            self.run([PYTHON, "scripts/build_site.py", "--repository", REPOSITORY])
        if before != self.fingerprint():
            raise RuntimeError("Files changed during validation; waiting for stable edits.")
        self.guard()
        if changed:
            self.git("add", "--all")
            if before != self.fingerprint():
                raise RuntimeError("Files changed while staging; waiting for stable edits.")
            if self.git("diff", "--cached", "--quiet", check=False).returncode == 1:
                self.git("commit", "-m", "Auto-sync local updates " + time.strftime("%Y-%m-%d %H:%M:%S"))
        self.git("push", "origin", "HEAD:refs/heads/main")
        return "pushed " + self.git("rev-parse", "--short", "HEAD").stdout.strip()


def write_status(state_dir, **values):
    target = state_dir / "status.json"
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(dict(pid=os.getpid(), updated_at=time.strftime("%Y-%m-%d %H:%M:%S"), **values), indent=2), encoding="utf-8")
    temporary.replace(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll", type=float, default=5)
    parser.add_argument("--quiet", type=float, default=15)
    args = parser.parse_args()
    sync = Sync()
    state = Path(sync.git("rev-parse", "--absolute-git-dir").stdout.strip()) / "auto-sync"
    state.mkdir(exist_ok=True)
    handler = RotatingFileHandler(state / "sync.log", maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    LOG.setLevel(logging.INFO)
    LOG.addHandler(handler)
    # The OS releases this lock even after a crash; duplicate launches exit.
    with (state / "worker.lock").open("a+b") as lock:
        lock.write(b"0")
        lock.flush()
        lock.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return 0
        LOG.info("Started auto-sync for %s", ROOT)
        if args.once:
            outcome = sync.sync()
            write_status(state, state=outcome)
            LOG.info(outcome)
            return 0
        previous = None
        stable_since = time.monotonic()
        attempted = None
        retry_at = 0.0
        while True:
            try:
                if (state / "paused").exists():
                    write_status(state, state="paused")
                    previous = attempted = None
                    time.sleep(max(1, args.poll))
                    continue
                current = sync.fingerprint() + sync.git("rev-parse", "HEAD").stdout.strip()
                now = time.monotonic()
                if current != previous:
                    previous, stable_since = current, now
                    write_status(state, state="waiting for stable edits")
                elif now - stable_since >= args.quiet and (current != attempted or now >= retry_at):
                    outcome = sync.sync()
                    LOG.info(outcome)
                    attempted = current
                    retry_at = now + 60
                    write_status(state, state=outcome)
                time.sleep(max(1, args.poll))
            except Exception as error:
                LOG.error("%s", error)
                write_status(state, state="retrying", error=str(error))
                time.sleep(60)


if __name__ == "__main__":
    raise SystemExit(main())