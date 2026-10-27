"""Offline guards for deleting the retired private report branch."""
import pathlib
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "scripts"))
import retire_old_report_branch as c
from private_repo import ApiError

def b(sha):
    return {"sha": sha, "type": "blob", "mode": "100644"}

class RetirementGuards(unittest.TestCase):
    def test_safe_branch_deletes_only_frozen_ref(self):
        old = {p: b("same") for p in c.LEDGERS}
        old["AGENTS.md"] = b("obsolete-doc")
        current = dict(old, **{"AGENTS.md": b("main-doc")})
        with patch.object(c, "ref_head", side_effect=["main-sha", c.EXPECTED, c.EXPECTED, ApiError(404, "ref")]), \
             patch.object(c, "tree_snapshot", side_effect=[("main-tree",current), ("old-tree",old)]), \
             patch.object(c, "api") as api:
            c.retire()
        api.assert_called_once_with(c.DEFAULT_REPO, "git/refs/heads/" + c.BRANCH, "DELETE")

    def test_moved_ref_fails_without_delete(self):
        with patch.object(c, "ref_head", side_effect=["main-sha","unexpected"]), \
             patch.object(c, "api") as api:
            with self.assertRaisesRegex(RuntimeError,"changed"):
                c.retire()
        api.assert_not_called()

    def test_changed_receipts_fail_without_delete(self):
        old = {p: b("same") for p in c.LEDGERS}
        main = dict(old)
        main[c.LEDGERS[0]] = b("different")
        with patch.object(c, "ref_head", side_effect=["main-sha",c.EXPECTED]), \
             patch.object(c, "tree_snapshot", side_effect=[("main-tree",main), ("old-tree",old)]), \
             patch.object(c, "api") as api:
            with self.assertRaisesRegex(RuntimeError,"ledger"):
                c.retire()
        api.assert_not_called()

    def test_unique_old_report_fails_without_delete(self):
        old = {p: b("same") for p in c.LEDGERS}
        old["reports/finance/unique.md"]=b("content")
        main = {p: b("same") for p in c.LEDGERS}
        with patch.object(c, "ref_head", side_effect=["main-sha",c.EXPECTED]), \
             patch.object(c, "tree_snapshot", side_effect=[("main-tree",main),("old-tree",old)]), \
             patch.object(c, "api") as api:
            with self.assertRaisesRegex(RuntimeError,"unique paths"):
                c.retire()
        api.assert_not_called()
