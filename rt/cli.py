"""Main CLI entry point for Ritza Tools"""

import click
from rt.commands import cgd, comments


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Ritza Tools - CLI for document conversion and access"""
    pass


# Register commands
main.add_command(cgd.cgd)
main.add_command(comments.comments)


if __name__ == "__main__":
    main()
