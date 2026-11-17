"""Start a marimo notebook server without ever showing a console window.

Usage (Windows, from a GUI app or an agent):

    pythonw scripts/launch_notebook.pyw notebooks/health/weight.py --port 27180 --watch
    pythonw scripts/launch_notebook.pyw notebooks/health/weight.py --port 27180 \
        -- --update-latest true

Why this exists
---------------
On Windows a console-subsystem program started from a process that has no
console of its own is handed a *brand-new* console. When Windows Terminal is
the registered default terminal, the OS brokers that console to
``WindowsTerminal.exe -Embedding``, which opens a large black window over the
screen and keeps it open for as long as the server runs.

``uvx marimo edit ...`` is such a program: ``uvx``/``uv`` are console apps, so
launching a notebook from a GUI application (an agent host, a file manager, a
desktop shortcut) pops that window up and leaves it there.

The fix has two halves:

1. This file uses a ``.pyw`` extension, so Windows launches it with
   ``pythonw.exe`` (GUI subsystem). A GUI-subsystem process never claims a
   console, so nothing is inherited into the tree.
2. Every child is started with ``CREATE_NO_WINDOW``, which gives the child a
   console that has no window. Descendants inherit that hidden console, so the
   whole ``uvx -> marimo -> python -> uv -> python`` tree stays invisible.

Server output is written to a log file instead of a console; the URL is also
written to a sibling ``.url`` file so a caller can pick it up without parsing
logs.
"""

from __future__ import annotations

import argparse
import os
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

IS_WINDOWS = os.name == "nt"

# Windows creation flags. CREATE_NO_WINDOW gives a console application a
# console without a visible window; DETACHED_PROCESS does not (it still shows
# one), so it is deliberately not used here.
CREATE_NO_WINDOW = 0x08000000 if IS_WINDOWS else 0
STARTF_USESHOWWINDOW = 0x00000001 if IS_WINDOWS else 0
SW_HIDE = 0

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = REPO_ROOT / "data" / "logs"


def _startup_info() -> subprocess.STARTUPINFO | None:
    """Hide the child's window even if the flags above are ignored."""
    if not IS_WINDOWS:
        return None
    info = subprocess.STARTUPINFO()
    info.dwFlags |= STARTF_USESHOWWINDOW
    info.wShowWindow = SW_HIDE
    return info


def build_command(args: argparse.Namespace) -> list[str]:
    """Assemble the ``uvx marimo edit ...`` command line."""
    uvx = shutil.which("uvx")
    if uvx is None:
        uv = shutil.which("uv")
        if uv is None:
            raise SystemExit(
                "Neither 'uvx' nor 'uv' is on PATH. Install uv: https://docs.astral.sh/uv/"
            )
        uvx = uv
        base = [uv, "tool", "run"]
    else:
        base = [uvx]

    cmd = [
        *base,
        "marimo",
        "edit",
        str(Path(args.notebook).resolve()),
        "--port",
        str(args.port),
        "--host",
        args.host,
        "--skip-update-check",
    ]
    if not args.no_sandbox:
        cmd.append("--sandbox")
    if args.watch:
        cmd.append("--watch")
    if args.headless:
        cmd.append("--headless")
    if args.token_file:
        cmd += ["--token-password-file", str(Path(args.token_file).resolve())]
    cmd += list(args.extra)
    return cmd


def write_token(token_file: Path) -> str:
    """Generate a token password and hand its path to marimo."""
    token = secrets.token_urlsafe(24)
    token_file.parent.mkdir(parents=True, exist_ok=True)
    token_file.write_text(token, encoding="utf-8")
    try:
        token_file.chmod(0o600)
    except OSError:  # pragma: no cover - best effort on Windows
        pass
    return token


def spawn(cmd: list[str], log_path: Path) -> subprocess.Popen[bytes]:
    """Start the server with no visible console."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_handle = open(log_path, "ab", buffering=0)
    log_handle.write(
        f"\n=== launch {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n"
        f"=== command: {' '.join(cmd)}\n\n".encode()
    )
    kwargs: dict[str, object] = {
        "stdout": log_handle,
        "stderr": subprocess.STDOUT,
        "stdin": subprocess.DEVNULL,
        "cwd": str(REPO_ROOT),
        "creationflags": CREATE_NO_WINDOW,
    }
    if IS_WINDOWS:
        kwargs["startupinfo"] = _startup_info()
    try:
        return subprocess.Popen(cmd, **kwargs)  # noqa: S603
    finally:
        # The child has its own duplicate of the handle; releasing the parent's
        # copy keeps the log from staying locked after the launcher exits.
        log_handle.close()


def _fail(message: str, log_path: Path | None = None) -> None:
    """Report a fatal error.

    Under ``pythonw.exe`` there is no console, so a bare ``print`` would be
    lost. The message is therefore also appended to the log file.
    """
    if log_path is not None:
        try:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as handle:
                handle.write(f"=== launch failed: {message}\n")
        except OSError:
            pass
    if sys.stderr is not None:
        sys.stderr.write(message + "\n")
    raise SystemExit(message)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="launch_notebook.pyw",
        description="Launch a marimo notebook without showing a console window.",
    )
    parser.add_argument("notebook", help="Path to the notebook .py file.")
    parser.add_argument("--port", type=int, default=2718, help="Port to serve on.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind.")
    parser.add_argument("--watch", action="store_true", help="Reload on file changes.")
    parser.add_argument(
        "--no-sandbox",
        action="store_true",
        help="Do not use marimo's isolated environment (uses the ambient env).",
    )
    parser.add_argument(
        "--no-headless",
        dest="headless",
        action="store_false",
        help="Open the notebook in a browser (default: serve only).",
    )
    parser.add_argument(
        "--token-file",
        default=None,
        help=(
            "Generate a token, write it here, and hand it to marimo. The file "
            "then holds the access token to use as 'Authorization: Bearer <token>'."
        ),
    )
    parser.add_argument("--log", default=None, help="Log file path.")
    parser.add_argument(
        "--detach",
        action="store_true",
        help="Return immediately instead of waiting for the server.",
    )
    parser.set_defaults(headless=True)

    # Everything after a bare "--" is forwarded to marimo untouched. This is
    # split by hand rather than with argparse.REMAINDER, which mis-parses
    # optionals that follow the first positional.
    own_args = list(argv if argv is not None else sys.argv[1:])
    extra: list[str] = []
    if "--" in own_args:
        separator = own_args.index("--")
        own_args, extra = own_args[:separator], own_args[separator + 1 :]

    args = parser.parse_args(own_args)
    args.extra = extra

    notebook = Path(args.notebook)
    stem = notebook.stem
    log_path = Path(args.log).resolve() if args.log else LOG_DIR / f"{stem}.log"
    url_path = log_path.with_suffix(".url")

    if not notebook.is_file():
        _fail(f"Notebook not found: {notebook}", log_path)

    if args.token_file:
        token = write_token(Path(args.token_file).resolve())
    else:
        token = None

    try:
        cmd = build_command(args)
    except SystemExit as error:
        _fail(str(error), log_path)

    process = spawn(cmd, log_path)

    url = f"http://{args.host}:{args.port}/"
    if token:
        url = f"{url}?access_token={token}"
    url_path.parent.mkdir(parents=True, exist_ok=True)
    url_path.write_text(url, encoding="utf-8")

    if args.detach:
        if sys.stderr is not None:
            sys.stderr.write(f"pid={process.pid} url={url} log={log_path}\n")
        return 0

    try:
        return process.wait()
    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
