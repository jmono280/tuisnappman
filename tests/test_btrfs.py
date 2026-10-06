from tuisnappman.services import btrfs


def test_snapshot_path():
    assert btrfs.snapshot_path("/home", 568) == "/home/.snapshots/568/snapshot"
    assert btrfs.snapshot_path("/", 5) == "/.snapshots/5/snapshot"


def test_parse_du_returns_exclusive_column():
    out = "     Total   Exclusive  Set shared  Filename\n 200 4096 0 /home/.snapshots/1/snapshot\n"
    assert btrfs.parse_du(out) == 4096


def test_parse_du_garbage_returns_none():
    assert btrfs.parse_du("nada útil") is None


def test_exclusive_bytes_uses_fake(fake_runner):
    assert btrfs.exclusive_bytes(fake_runner, "/home", 568) == 107374182400
