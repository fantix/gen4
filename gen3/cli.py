import click
import pkg_resources


@click.group()
def gen3():
    """Welcome to Gen3 Data Commons."""


for ep in pkg_resources.iter_entry_points("gen3.cli"):
    ep.load()
