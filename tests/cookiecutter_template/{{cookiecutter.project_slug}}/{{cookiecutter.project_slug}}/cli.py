"""Console script for {{ cookiecutter.project_slug }}."""
import sys

import click


@click.command()
def main(args=None):
    """Console script entry point."""
    click.echo("Replace this message by putting your code into {{ cookiecutter.project_slug }}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
