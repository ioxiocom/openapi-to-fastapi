import re
from pathlib import Path

from invoke import Exit, task


@task
def release(ctx):
    toml = Path("pyproject.toml").read_text()
    match = re.search(r'version = "(.*?)"', toml)
    if match:
        version = match.group(1)
        print(f"Releasing v{version}")
        ctx.run(f"git tag v{version}")
        ctx.run(f"git tag v{version}")
    else:
        print("Failed to find version in the pyproject.toml")


def run_test_cmd(ctx, cmd) -> int:
    print("=" * 79)
    print(f"> {cmd}")
    return ctx.run(cmd, warn=True).exited


@task
def test(ctx):
    failed_commands = []
    if run_test_cmd(ctx, "pre-commit run --all-files"):
        failed_commands.append("Pre commit hooks")
    if run_test_cmd(ctx, "mypy openapi_to_fastapi"):
        failed_commands.append("Mypy")
    if run_test_cmd(ctx, "pytest"):
        failed_commands.append("Unit tests")
    if run_test_cmd(ctx, "flake8"):
        failed_commands.append("flake8")

    if failed_commands:
        msg = "Errors: " + ", ".join(failed_commands)
        raise Exit(message=msg, code=len(failed_commands))
