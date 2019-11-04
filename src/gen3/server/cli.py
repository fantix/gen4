import logging
import ssl
import subprocess
import typing

import click

from ..cli import gen3

LOG_LEVELS = {
    "critical": logging.CRITICAL,
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
}
LEVEL_CHOICES = click.Choice(LOG_LEVELS.keys())
SSL_PROTOCOL_VERSION = getattr(ssl, "PROTOCOL_TLS", ssl.PROTOCOL_SSLv23)


@gen3.command()
@click.option(
    "--host",
    type=str,
    default="127.0.0.1",
    help="Bind socket to this host.",
    show_default=True,
)
@click.option(
    "--port",
    type=int,
    default=8000,
    help="Bind socket to this port.",
    show_default=True,
)
@click.option("--uds", type=str, default=None, help="Bind to a UNIX domain socket.")
@click.option(
    "--fd", type=int, default=None, help="Bind to socket from this file descriptor."
)
@click.option(
    "--debug", is_flag=True, default=False, help="Enable debug mode.", hidden=True
)
@click.option(
    "--reload/--no-reload", is_flag=True, default=True, help="Enable auto-reload."
)
@click.option(
    "--reload-dir",
    "reload_dirs",
    multiple=True,
    help="Set reload directories explicitly, instead of using 'sys.path'.",
)
@click.option(
    "--workers",
    default=None,
    type=int,
    help="Number of worker processes. Defaults to the $WEB_CONCURRENCY environment "
    "variable if available. Not valid with --reload.",
)
@click.option(
    "--env-file",
    type=click.Path(exists=True),
    default=None,
    help="Environment configuration file.",
    show_default=True,
)
@click.option(
    "--log-config",
    type=click.Path(exists=True),
    default=None,
    help="Logging configuration file.",
    show_default=True,
)
@click.option(
    "--log-level",
    type=LEVEL_CHOICES,
    default=None,
    help="Log level. [default: info]",
    show_default=True,
)
@click.option(
    "--access-log/--no-access-log",
    is_flag=True,
    default=True,
    help="Enable/Disable access log.",
)
@click.option(
    "--proxy-headers/--no-proxy-headers",
    is_flag=True,
    default=True,
    help="Enable/Disable X-Forwarded-Proto, X-Forwarded-For, X-Forwarded-Port to "
    "populate remote address info.",
)
@click.option(
    "--forwarded-allow-ips",
    type=str,
    default=None,
    help="Comma seperated list of IPs to trust with proxy headers. Defaults to the "
    "$FORWARDED_ALLOW_IPS environment variable if available, or '127.0.0.1'.",
)
@click.option(
    "--root-path",
    type=str,
    default="",
    help="Set the ASGI 'root_path' for applications submounted below a given URL path.",
)
@click.option(
    "--limit-concurrency",
    type=int,
    default=None,
    help="Maximum number of concurrent connections or tasks to allow, before issuing "
    "HTTP 503 responses.",
)
@click.option(
    "--limit-max-requests",
    type=int,
    default=None,
    help="Maximum number of requests to service before terminating the process.",
)
@click.option(
    "--timeout-keep-alive",
    type=int,
    default=5,
    help="Close Keep-Alive connections if no new data is received within this timeout.",
    show_default=True,
)
@click.option(
    "--ssl-keyfile", type=str, default=None, help="SSL key file", show_default=True
)
@click.option(
    "--ssl-certfile",
    type=str,
    default=None,
    help="SSL certificate file",
    show_default=True,
)
@click.option(
    "--ssl-version",
    type=int,
    default=SSL_PROTOCOL_VERSION,
    help="SSL version to use (see stdlib ssl module's)",
    show_default=True,
)
@click.option(
    "--ssl-cert-reqs",
    type=int,
    default=ssl.CERT_NONE,
    help="Whether client certificate is required (see stdlib ssl module's)",
    show_default=True,
)
@click.option(
    "--ssl-ca-certs",
    type=str,
    default=None,
    help="CA certificates file",
    show_default=True,
)
@click.option(
    "--ssl-ciphers",
    type=str,
    default="TLSv1",
    help="Ciphers to use (see stdlib ssl module's)",
    show_default=True,
)
@click.option(
    "--header",
    "headers",
    multiple=True,
    help="Specify custom default HTTP response headers as a Name:Value pair",
)
@click.option(
    "--web",
    type=click.Path(),
    default="web",
    help="Specify where the source of the web frontend is.",
)
@click.option("--no-web", is_flag=True)
def run(
    host: str,
    port: int,
    uds: str,
    fd: int,
    debug: bool,
    reload: bool,
    reload_dirs: typing.List[str],
    workers: int,
    env_file: str,
    log_config: str,
    log_level: str,
    access_log: bool,
    proxy_headers: bool,
    forwarded_allow_ips: str,
    root_path: str,
    limit_concurrency: int,
    limit_max_requests: int,
    timeout_keep_alive: int,
    ssl_keyfile: str,
    ssl_certfile: str,
    ssl_version: int,
    ssl_cert_reqs: int,
    ssl_ca_certs: str,
    ssl_ciphers: str,
    headers: typing.List[str],
    web: str,
    no_web: bool,
):
    """Run Gen3 server."""
    import uvicorn

    if reload:
        app = "gen3.server.app:app"
    else:
        from .app import app

    kwargs = {
        "app": app,
        "host": host,
        "port": port,
        "uds": uds,
        "fd": fd,
        "loop": "auto",
        "http": "auto",
        "ws": "auto",
        "lifespan": "auto",
        "env_file": env_file,
        "log_config": uvicorn.config.LOGGING_CONFIG
        if log_config is None
        else log_config,
        "log_level": log_level,
        "access_log": access_log,
        "interface": "auto",
        "debug": debug,
        "reload": reload,
        "reload_dirs": reload_dirs if reload_dirs else None,
        "workers": workers,
        "proxy_headers": proxy_headers,
        "forwarded_allow_ips": forwarded_allow_ips,
        "root_path": root_path,
        "limit_concurrency": limit_concurrency,
        "limit_max_requests": limit_max_requests,
        "timeout_keep_alive": timeout_keep_alive,
        "ssl_keyfile": ssl_keyfile,
        "ssl_certfile": ssl_certfile,
        "ssl_version": ssl_version,
        "ssl_cert_reqs": ssl_cert_reqs,
        "ssl_ca_certs": ssl_ca_certs,
        "ssl_ciphers": ssl_ciphers,
        "headers": list([header.split(":") for header in headers]),
    }
    if web and not no_web:
        web_proc = subprocess.Popen(["yarn", "serve"], cwd=web)
    else:
        web_proc = None
    uvicorn.run(**kwargs)
    if web_proc is not None:
        web_proc.terminate()
        web_proc.wait(4)
        web_proc.kill()
