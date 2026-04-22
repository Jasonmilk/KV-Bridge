import click
import json
from kv_bridge.common import get_settings
from kv_bridge.core.shadow import ShadowTracker
from rich.console import Console
from rich.table import Table

@click.command(name="stats")
@click.option("--json", "as_json", is_flag=True, help="Output in JSON format")
def stats(as_json):
    """Show KV-Bridge cache statistics."""
    settings = get_settings()
    shadow_tracker = ShadowTracker(settings)
    shadow_stats = shadow_tracker.get_stats()

    if settings.memory_mode:
        from kv_bridge.core.metrics import get_metrics
        metrics = get_metrics()
        data = metrics.summary()
        data["shadow_tree"] = shadow_stats
        data["config"] = {
            "min_savings_threshold": settings.min_savings_threshold,
            "shadow_ttl_seconds": settings.shadow_ttl_seconds
        }
    else:
        from kv_bridge.core.vfd.indexer import VFDIndexer
        indexer = VFDIndexer(settings.vfd_index_path)
        vfd_count = indexer.count()
        data = {
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
        click.echo(json.dumps(data, indent=2))
    else:
        console = Console()
        table = Table(title="KV-Bridge Cache Statistics")
        table.add_column("Backend", style="cyan")
        table.add_column("Requests", justify="right")
        table.add_column("Tokens Saved", justify="right")
        table.add_column("Cost Saved", justify="right", style="green")
        for backend, stats in data.get("by_backend", {}).items():
            table.add_row(
                backend,
                str(stats["requests"]),
                f"{stats['tokens_saved']:,}",
                f"${stats['cost_saved']:.4f}"
            )
        console.print(table)
        console.print(f"[dim]Shadow prefixes: {shadow_stats['total_prefixes']}[/dim]")
        if not settings.memory_mode:
            console.print(f"[dim]vFD entries: {data['vfd_index']['total_entries']}/{data['vfd_index']['max_size']}[/dim]")
        console.print(f"[dim]Total requests: {data.get('total_requests', 0)}[/dim]")