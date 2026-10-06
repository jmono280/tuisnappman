from tuisnappman.cache import SizeCache, cache_key
from tuisnappman.models import Snapshot

SNAP = Snapshot("home", 568, "single", "2026-10-05 22:00:03", "timeline", "timeline")


def test_key_includes_date():
    assert cache_key(SNAP) == "home:568:2026-10-05 22:00:03"


def test_set_save_and_reload(tmp_path):
    path = tmp_path / "sub" / "sizes.json"
    cache = SizeCache(path)
    cache.set("a", 100)
    assert cache.save() is True
    assert SizeCache(path).get("a") == 100


def test_missing_or_corrupt_file_gives_empty_cache(tmp_path):
    assert SizeCache(tmp_path / "nope.json").get("a") is None
    bad = tmp_path / "bad.json"
    bad.write_text("{no es json")
    assert SizeCache(bad).get("a") is None


def test_wrong_version_is_ignored(tmp_path):
    path = tmp_path / "v.json"
    path.write_text('{"version": 999, "entries": {"a": {"bytes": 1}}}')
    assert SizeCache(path).get("a") is None


def test_prune_drops_vanished_snapshots(tmp_path):
    cache = SizeCache(tmp_path / "s.json")
    cache.set("a", 1)
    cache.set("b", 2)
    cache.prune({"a"})
    assert cache.get("a") == 1
    assert cache.get("b") is None


def test_save_failure_is_not_fatal(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    cache = SizeCache(blocker / "sizes.json")  # el padre es un archivo
    cache.set("a", 1)
    assert cache.save() is False
