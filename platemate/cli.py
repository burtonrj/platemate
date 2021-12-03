"""Console script for platemate."""

import click


@click.command()
def main():
    """Main entrypoint."""
    click.echo("platemate")
    click.echo("=" * len("platemate"))
    click.echo("Python package for plate based assays like ELISAs or Luminex")


if __name__ == "__main__":
    main()  # pragma: no cover
