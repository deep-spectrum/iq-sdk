from __future__ import annotations
import pathlib
from typing import Annotated
from tyro.extras import SubcommandApp
import xxhash
from rich.console import Console
import yaml
import tyro

app = SubcommandApp()
console = Console()


@app.command
def verify(trace: pathlib.Path, /,
           verbose: Annotated[tyro.conf.UseCounterAction[int], tyro.conf.arg(aliases=["-v"])] = 0) -> None:
    """Verify the files in a capture run.

    Args:
        trace: Path to the trace directory to verify. Must contain a checksum.yaml file.
        verbose: Verbose mode
    """

    verbose = verbose > 0

    if not trace.exists():
        console.print(f"{trace} does not exist")
        exit(1)
    if not trace.is_dir():
        console.print(f"{trace} is not a directory")
        exit(1)
    checksum_file = trace / "checksum.yaml"
    if not checksum_file.exists():
        console.print(f"{checksum_file} does not exist")
        exit(1)

    with open(checksum_file, "r") as f:
        checksums: dict[str, str] = yaml.safe_load(f)

    seed = int(checksums['seed'], 16)
    del checksums['seed']

    def check_file(file_: pathlib.Path, crc_: str | None) -> bool:
        if not file_.exists():
            if crc is not None:
                console.print(f"{file.name}: [red]Does not exist[/red]")
                return False
            return True
        with open(file_, "rb") as f:
            buffer = f.read()
        calculated = xxhash.xxh64(buffer, seed).hexdigest()
        ret = calculated == crc_
        if ret and verbose:
            console.print(f"{file.name}: [green]OK[/green]")
        elif not ret:
            console.print(f"{file.name}: [red]Failed ({calculated} != {crc_})[/red]")
        return ret

    ok = True
    for file, crc in checksums.items():
        ok = check_file(trace / file, crc)

    if not ok:
        console.print("[red]One or more files in the trace has data integrity issues[/red]")
        exit(1)
    console.print("All files are valid")


def main():
    app.cli()


if __name__ == '__main__':
    main()
