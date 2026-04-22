import click
import json
from pathlib import Path
from kv_bridge.common import get_settings, logger
from kv_bridge.core.shadow import ShadowTracker

@click.command(name="shadow")
@click.argument("log_file", type=click.Path(exists=True))
@click.option("--analyze", is_flag=True, help="Analyze historical cache performance")
def shadow(log_file, analyze):
    """Run shadow mode analysis on historical logs."""
    settings = get_settings()
    tracker = ShadowTracker(settings)
    
    log_path = Path(log_file)
    click.echo(f"Analyzing log file: {log_path}")
    
    hits = 0
    misses = 0
    total_saved = 0
    
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line.strip())
                if "hit_verified" in entry:
                    if entry["hit_verified"]:
                        hits += 1
                        total_saved += entry.get("saved_tokens", 0)
                    else:
                        misses += 1
            except json.JSONDecodeError:
                continue
            except Exception as e:
                logger.warning("Failed to parse log line", error=str(e))
    
    total = hits + misses
    hit_rate = (hits / total) * 100 if total > 0 else 0
    
    click.echo("Shadow Mode Analysis Results")
    click.echo("============================")
    click.echo(f"Total requests analyzed: {total}")
    click.echo(f"Cache hits: {hits} ({hit_rate:.2f}%)")
    click.echo(f"Cache misses: {misses}")
    click.echo(f"Total tokens saved: {total_saved}")
    click.echo(f"Estimated cost saved: ${total_saved * 0.000003:.4f}")
