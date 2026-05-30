"""Command-line entrypoint: `peerpet <subcommand>`.

run     launch a shell with the pet (the host)
feed    feed the running pet
play    play with the running pet
pet     pet the running pet
status  print the pet's state as JSON (no host / TTY needed)
config  print resolved config + paths
"""

from __future__ import annotations

import argparse
import json
import sys

from peerpet import __version__
from peerpet.config import Config
from peerpet.interaction import ipc
from peerpet.memory.base import current_memory_key, get_memory
from peerpet.pet import behavior


def _interact(command: str) -> int:
    try:
        reply = ipc.send(command)
    except ipc.HostNotRunning as e:
        print(f"peerpet: {e}", file=sys.stderr)
        return 1
    if not reply.get("ok"):
        print(f"peerpet: {reply.get('error', 'unknown error')}", file=sys.stderr)
        return 1
    state = reply["state"]
    print(
        f"{state['name']} is now {state['mood']} "
        f"(hunger {int(state['hunger'])}, happiness {int(state['happiness'])})"
    )
    return 0


def _cmd_status(_: argparse.Namespace) -> int:
    """Works without a running host: read, settle to now, print."""
    memory = get_memory()
    key = current_memory_key()
    state = behavior.tick(memory.load(key))
    memory.save(key, state)
    memory.close()
    print(json.dumps(state.to_dict(), indent=2))
    return 0


def _cmd_config(_: argparse.Namespace) -> int:
    cfg = Config.load()
    print(
        json.dumps(
            {
                "config_path": str(
                    __import__("peerpet.config", fromlist=["config_path"]).config_path()
                ),
                "socket_path": str(ipc.socket_path()),
                "pet_name": cfg.pet_name,
                "pet_rows": cfg.pet_rows,
                "tick_interval": cfg.tick_interval,
                "shell": cfg.resolved_shell,
                "use_honcho": cfg.use_honcho,
            },
            indent=2,
        )
    )
    return 0


def _cmd_run(_: argparse.Namespace) -> int:
    from peerpet.host import pty_host

    return pty_host.run(Config.load())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="peerpet", description=__doc__)
    parser.add_argument("--version", action="version", version=f"peerpet {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("run", help="launch a shell with the pet").set_defaults(func=_cmd_run)
    sub.add_parser("status", help="print pet state as JSON").set_defaults(func=_cmd_status)
    sub.add_parser("config", help="print resolved config").set_defaults(func=_cmd_config)

    for cmd, help_text in [
        ("feed", "feed the running pet"),
        ("play", "play with the running pet"),
        ("pet", "pet the running pet"),
    ]:
        p = sub.add_parser(cmd, help=help_text)
        p.set_defaults(func=lambda _ns, c=cmd: _interact(c))

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
