import click
from kv_bridge.common import configure_logging, get_settings

@click.group()
@click.version_option(version="0.1.0")
def cli():
    """KV-Bridge: Context Memory Allocator for AI Agents."""
    # Initialize logging
    configure_logging()

# Import subcommands
from . import server, stats, shadow
cli.add_command(server.server)
cli.add_command(stats.stats)
cli.add_command(shadow.shadow)

if __name__ == "__main__":
    cli()
