import click
import json
from kv_bridge.common import get_settings
from kv_bridge.core.shadow import ShadowTracker
from kv_bridge.core.vfd.indexer import VFDIndexer

@click.command(name="stats")
@click.option("--json", "as_json", is_flag=True, help="Output in JSON format")
def stats(as_json):
    """Show KV-Bridge cache statistics."""
    settings = get_settings()
    
    # Get shadow tree stats
    shadow_tracker = ShadowTracker(settings)
    shadow_stats = shadow_tracker.get_stats()
    
    # Get vFD index stats
    indexer = VFDIndexer(settings.vfd_index_path)
    vfd_count = indexer.count()
    
    stats_data = {
        "shadow_tree": shadow_stats,
        "vfd_index": {
            "total_entries": vfd_count,
            "max_size": settings.lru_max_size
        },
        "config": {
            "min_savings_threshold": settings.min_savings_threshold,
            "shadow_ttl_seconds": settings.shadow_ttl_seconds
        }
    }
    
    if as_json:
        click.echo(json.dumps(stats_data, indent=2))
    else:
        click.echo("KV-Bridge Statistics")
        click.echo("===================")
        click.echo(f"Shadow Tree: {shadow_stats['total_prefixes']} cached prefixes")
        click.echo(f"vFD Index: {vfd_count}/{settings.lru_max_size} entries")
        click.echo(f"Shadow TTL: {settings.shadow_ttl_seconds}s")
        click.echo(f"Min Savings Threshold: {settings.min_savings_threshold} tokens")
