import click
import pkg_resources


@click.group()
def gen3():
    """Welcome to Gen3 Data Commons."""


def load_extras():
    extras = {}
    for i, ep in enumerate(pkg_resources.iter_entry_points("gen3.cli")):
        try:
            ep.load()
        except pkg_resources.DistributionNotFound:
            for extra in ep.extras:
                extras.setdefault(extra, set()).add(ep.module_name)
    if extras:
        gen3.help += "\n\nExtra CLI modules not installed:\n\n\b\n"
        for extra, modules in extras.items():
            gen3.help += f"    gen3[{extra}]: {', '.join(modules)}\n"


load_extras()
