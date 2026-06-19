from __future__ import annotations
import pathlib
from tyro.extras import SubcommandApp
import xxhash
from rich.console import Console
import yaml

app = SubcommandApp()
console = Console()


def check_file(file: pathlib.Path, crc: str | None, seed: int) -> bool:
    if not file.exists():
        if crc is not None:
            console.print(f"{file.name}: [red]Does not exist[/red]")
            return False
        return True
    with open(file, "rb") as f:
        buffer = f.read()
    calculated = xxhash.xxh64(buffer, seed).hexdigest()
    ret = calculated == crc
    if ret:
        console.print(f"{file.name}: [green]OK[/green]")
    else:
        console.print(f"{file.name}: [red]Failed ({calculated} != {crc})[/red]")
    return ret


@app.command
def verify(trace: pathlib.Path, /) -> None:
    """Verify the files in a capture run.

    Args:
        trace: Path to the trace directory to verify. Must contain a checksum.yaml file.
    """
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

    ok = True
    for file, crc in checksums.items():
        ok = check_file(trace / file, crc, seed)

    if not ok:
        console.print("[red]One or more files in the trace has data integrity issues[/red]")
        exit(1)
    console.print("All files are valid")


def main():
    app.cli()


if __name__ == '__main__':
    main()
