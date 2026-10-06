"""Envoltorio de `snapper`. No importa Textual.

TODO: el formato de `snapper --jsonout` no está verificado contra una salida
real; el parser es tolerante. Sustituir tests/fixtures por la salida real de
`sudo snapper --jsonout -c home list`.
"""

import json

from tuisnappman.models import Config, Snapshot
from tuisnappman.runner import Result, Runner


def list_configs(runner: Runner) -> list[Config]:
    out = runner.run(["snapper", "--jsonout", "list-configs"]).check().stdout
    data = json.loads(out)
    items = data.get("configs", []) if isinstance(data, dict) else data
    return [Config(name=i.get("config") or i["name"], subvolume=i["subvolume"]) for i in items]


def list_snapshots(runner: Runner, config: str) -> list[Snapshot]:
    out = runner.run(["snapper", "--jsonout", "-c", config, "list"]).check().stdout
    data = json.loads(out)
    items = data.get(config, []) if isinstance(data, dict) else data
    return [
        Snapshot(
            config=config,
            number=int(i["number"]),
            kind=i.get("type") or "",
            date=i.get("date") or "",
            cleanup=i.get("cleanup") or "",
            description=i.get("description") or "",
        )
        for i in items
    ]


def delete_snapshots(runner: Runner, config: str, numbers: list[int]) -> Result:
    command = ["snapper", "-c", config, "delete", *map(str, numbers)]
    return runner.run(command, write=True).check()


def create_snapshot(runner: Runner, config: str, description: str) -> Result:
    command = ["snapper", "-c", config, "create", "-t", "single", "-d", description]
    return runner.run(command, write=True).check()
