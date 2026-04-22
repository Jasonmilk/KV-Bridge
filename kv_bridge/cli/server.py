import click
from kv_bridge.gateway import start_server

@click.command(name="server")
@click.option("--host", help="Listen host address")
@click.option("--port", type=int, help="Listen port")
def server(host, port):
    """Start the KV-Bridge gateway server."""
    # Override settings if provided
    from kv_bridge.common import get_settings
    settings = get_settings()
    if host:
        settings.host = host
    if port:
        settings.port = port
    
    click.echo(f"Starting KV-Bridge server on {settings.host}:{settings.port}")
    click.echo(f"Default backend: {settings.default_backend}")
    start_server()
