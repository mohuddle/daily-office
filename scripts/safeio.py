"""Descriptor-bound reads/writes and capped HTTPS fetches."""

from __future__ import annotations

import json
import os
import stat
import urllib.error
import urllib.request
from pathlib import Path

MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_TEXT_BYTES = 8 * 1024 * 1024
MAX_KEY_BYTES = 8192
MAX_HTTP_BYTES = 8 * 1024 * 1024


class IoError(RuntimeError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        return None


def _open_nofollow(path: Path, flags: int, mode: int = 0o600) -> int:
    path = Path(path)
    if not path.is_absolute():
        path = path.resolve()
    return os.open(str(path), flags | os.O_NOFOLLOW | os.O_CLOEXEC, mode)


def read_bytes(path: Path, max_bytes: int, *, require_private: bool = False) -> bytes:
    path = Path(path)
    try:
        fd = os.open(
            str(path),
            os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
        )
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise IoError(f"cannot open {path.name}") from exc
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise IoError(f"{path.name} is not a regular file")
        if st.st_nlink != 1:
            raise IoError(f"{path.name} has extra links")
        if require_private and (st.st_mode & 0o077):
            raise IoError(f"{path.name} must be mode 0600")
        if st.st_size > max_bytes:
            raise IoError(f"{path.name} exceeds size limit")
        os.set_blocking(fd, True)
        data = b""
        while len(data) <= max_bytes:
            chunk = os.read(fd, min(65536, max_bytes + 1 - len(data)))
            if not chunk:
                break
            data += chunk
        if len(data) > max_bytes:
            raise IoError(f"{path.name} grew past the limit")
        return data
    finally:
        os.close(fd)


def read_text(path: Path, max_bytes: int, encoding: str = "utf-8") -> str:
    return read_bytes(path, max_bytes).decode(encoding)


def read_json(path: Path, max_bytes: int = MAX_JSON_BYTES):
    return json.loads(read_text(path, max_bytes))


def write_bytes(path: Path, data: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.parent / f".{path.name}.{os.urandom(8).hex()}.tmp"
    fd = os.open(
        str(tmp),
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o600,
    )
    try:
        os.fchmod(fd, 0o600)
        view = memoryview(data)
        while view:
            n = os.write(fd, view)
            if n <= 0:
                raise IoError("short write")
            view = view[n:]
        os.fsync(fd)
        os.replace(tmp, path)
        tmp = None  # type: ignore[assignment]
        dirfd = os.open(str(path.parent), os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    except BaseException:
        if tmp is not None:
            try:
                os.unlink(tmp)
            except OSError:
                pass
        raise
    finally:
        os.close(fd)


def write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    write_bytes(path, text.encode(encoding))


def write_json(path: Path, value: object, **dumps_kw: object) -> None:
    payload = json.dumps(value, **dumps_kw)
    if not payload.endswith("\n"):
        payload += "\n"
    write_text(path, payload)


def fetch_bytes(
    url: str,
    *,
    max_bytes: int = MAX_HTTP_BYTES,
    timeout: int = 60,
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    method: str | None = None,
) -> bytes:
    if not url.startswith("https://"):
        raise IoError("only https URLs are allowed")
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(req, timeout=timeout) as resp:
            raw_length = resp.headers.get("Content-Length")
            if raw_length is not None:
                try:
                    declared = int(raw_length)
                except ValueError as exc:
                    raise IoError("invalid Content-Length") from exc
                if declared > max_bytes:
                    raise IoError("response too large")
            buf = bytearray()
            while True:
                remaining = max_bytes + 1 - len(buf)
                chunk = resp.read(min(65536, remaining))
                if not chunk:
                    break
                buf += chunk
                if len(buf) > max_bytes:
                    raise IoError("response too large")
            return bytes(buf)
    except urllib.error.HTTPError as exc:
        exc.read(4096)
        raise
