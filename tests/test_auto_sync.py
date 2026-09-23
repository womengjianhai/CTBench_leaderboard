"""Integration tests use temporary local Git remotes; they never contact GitHub."""
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("auto_sync", ROOT / "scripts/auto_sync.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class AutoSyncTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name)
        self.remote = base / "remote.git"
        self.work = base / "work"
        subprocess.run(["git", "init", "--bare", str(self.remote)], check=True, capture_output=True)
        subprocess.run(["git", "init", "-b", "main", str(self.work)], check=True, capture_output=True)
        self.git("config", "user.name", "Sync Test")
        self.git("config", "user.email", "sync@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.autocrlf", "false")
        (self.work / "README.md").write_text("initial\n", encoding="utf-8")
        (self.work / ".gitignore").write_text((ROOT / ".gitignore").read_text(encoding="utf-8"), encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-m", "initial")
        self.git("remote", "add", "origin", str(self.remote))
        self.git("push", "-u", "origin", "main")
        self.sync = module.Sync(self.work, remote=str(self.remote), validate=False)

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.work, check=True, capture_output=True, text=True, encoding="utf-8").stdout.strip()

    def remote_head(self):
        return subprocess.run(["git", "--git-dir", str(self.remote), "rev-parse", "main"], check=True, capture_output=True, text=True).stdout.strip()

    def test_add_modify_delete_ignore_and_noop(self):
        (self.work / "README.md").write_text("updated\n", encoding="utf-8")
        (self.work / "new.py").write_text("print('ready')\n", encoding="utf-8")
        (self.work / ".env").write_text("LOCAL_ONLY=example\n", encoding="utf-8")
        self.assertTrue(self.sync.sync().startswith("pushed"))
        head = self.git("rev-parse", "HEAD")
        self.assertEqual(self.remote_head(), head)
        self.assertNotIn(".env", self.git("ls-tree", "-r", "--name-only", "HEAD").splitlines())
        self.assertEqual(self.sync.sync(), "up-to-date")
        self.assertEqual(self.git("rev-parse", "HEAD"), head)
        (self.work / "new.py").unlink()
        self.assertTrue(self.sync.sync().startswith("pushed"))
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_validation_failure_keeps_changes_local(self):
        (self.work / "tests").mkdir()
        (self.work / "tests/test_site_build.py").write_text(
            "import unittest\nclass TestBroken(unittest.TestCase):\n def test_bad(self): self.fail('bad page')\n", encoding="utf-8")
        head = self.remote_head()
        self.sync.validate = True
        with self.assertRaises(RuntimeError):
            self.sync.sync()
        self.assertEqual(self.git("rev-parse", "HEAD"), head)
        self.assertEqual(self.remote_head(), head)
        self.assertTrue((self.work / "tests/test_site_build.py").exists())

    def test_remote_advance_is_never_overwritten(self):
        (self.work / "README.md").write_text("remote update\n", encoding="utf-8")
        self.git("add", ".")
        self.git("commit", "-m", "remote update")
        self.git("push")
        head = self.remote_head()
        self.git("reset", "--hard", "HEAD~1")
        (self.work / "README.md").write_text("local update\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "Remote main"):
            self.sync.sync()
        self.assertEqual(self.remote_head(), head)
        self.assertEqual((self.work / "README.md").read_text(encoding="utf-8"), "local update\n")

    def test_failed_push_is_retried_without_duplicate_commit(self):
        original_git = self.sync.git
        def fail_push(*args, **kwargs):
            if args[0] == "push":
                raise RuntimeError("Simulated connection loss")
            return original_git(*args, **kwargs)
        self.sync.git = fail_push
        (self.work / "README.md").write_text("pending\n", encoding="utf-8")
        with self.assertRaisesRegex(RuntimeError, "connection loss"):
            self.sync.sync()
        local_head = self.git("rev-parse", "HEAD")
        self.assertNotEqual(local_head, self.remote_head())
        self.sync.git = original_git
        self.sync.sync()
        self.assertEqual(self.remote_head(), local_head)
        self.assertEqual(self.git("rev-parse", "HEAD"), local_head)

    def test_other_branch_and_changed_remote_are_blocked(self):
        self.git("checkout", "-b", "draft")
        with self.assertRaisesRegex(RuntimeError, "branch main"):
            self.sync.sync()
        self.git("checkout", "main")
        self.git("remote", "set-url", "origin", str(self.remote.parent / "other.git"))
        with self.assertRaisesRegex(RuntimeError, "origin"):
            self.sync.sync()


    def test_worker_entrypoint_writes_status(self):
        from unittest.mock import patch
        import json
        (self.work / "README.md").write_text("worker update\n", encoding="utf-8")
        old_handlers = list(module.LOG.handlers)
        try:
            with patch.object(module, "Sync", return_value=self.sync), patch.object(module.sys, "argv", ["auto_sync.py", "--once"]):
                self.assertEqual(module.main(), 0)
            status = json.loads((self.work / ".git/auto-sync/status.json").read_text(encoding="utf-8"))
            self.assertTrue(status["state"].startswith("pushed"))
            self.assertEqual(self.remote_head(), self.git("rev-parse", "HEAD"))
        finally:
            for handler in list(module.LOG.handlers):
                if handler not in old_handlers:
                    module.LOG.removeHandler(handler)
                    handler.close()


if __name__ == "__main__":
    unittest.main()