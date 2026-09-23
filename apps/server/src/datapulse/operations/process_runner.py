"""Apply OS limits before executing a configured processor without a shell."""

import argparse
import os
import resource
import sys


def bounded_command(
    command: list[str], *, cpu_seconds: int = 30, memory_mb: int = 1024
) -> list[str]:
    return [
        sys.executable,
        "-m",
        "datapulse.operations.process_runner",
        "--cpu-seconds",
        str(cpu_seconds),
        "--memory-mb",
        str(memory_mb),
        "--",
        *command,
    ]


def processor_environment() -> dict[str, str]:
    environment = {
        name: os.environ[name]
        for name in ("PATH", "LANG", "LC_ALL", "TMPDIR", "TZ")
        if name in os.environ
    }
    environment.update(
        {
            name: "1"
            for name in (
                "OPENBLAS_NUM_THREADS",
                "OMP_NUM_THREADS",
                "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS",
            )
        }
    )
    # Arrow's default allocator reserves large virtual arenas that can exhaust
    # RLIMIT_AS even for a tiny Parquet file. Keep its allocations inside the
    # same address-space budget using the system allocator.
    environment["ARROW_DEFAULT_MEMORY_POOL"] = "system"
    # glibc otherwise reserves a separate arena for each native worker thread;
    # imports alone can consume nearly the entire 1 GiB virtual-memory budget.
    environment["MALLOC_ARENA_MAX"] = "2"
    return environment


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cpu-seconds", type=int, required=True)
    parser.add_argument("--memory-mb", type=int, required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command or args.cpu_seconds < 1 or args.memory_mb < 64:
        parser.error("A command and positive limits are required.")
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_CPU, (args.cpu_seconds, args.cpu_seconds))
    resource.setrlimit(resource.RLIMIT_FSIZE, (512 * 1024 * 1024, 512 * 1024 * 1024))
    if sys.platform.startswith("linux"):
        memory = args.memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    try:
        os.execvpe(command[0], command, processor_environment())
    except FileNotFoundError:
        sys.exit(127)
    except PermissionError:
        sys.exit(126)


if __name__ == "__main__":
    main()
