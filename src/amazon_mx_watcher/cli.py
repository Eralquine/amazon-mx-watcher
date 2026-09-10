from __future__ import annotations

import logging
from pathlib import Path

import click

from .config import AppConfig, ProductConfig, load_env, load_products_file, save_products_file
from .monitor import run_forever, run_once
from .storage import StateStore

DEFAULT_PRODUCTS_PATH = Path("products.yaml")
DEFAULT_DB_PATH = Path("data/state.db")


def _configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


@click.group()
@click.option(
    "--products-file",
    type=click.Path(path_type=Path),
    default=DEFAULT_PRODUCTS_PATH,
    show_default=True,
    help="Ruta al archivo de configuración de productos.",
)
@click.pass_context
def main(ctx: click.Context, products_file: Path) -> None:
    """Amazon MX Watcher: monitorea stock y precio en amazon.com.mx."""
    _configure_logging()
    load_env()
    ctx.ensure_object(dict)
    ctx.obj["products_file"] = products_file


@main.command()
@click.option("--once", is_flag=True, help="Revisa una sola vez y termina, en vez de correr en bucle.")
@click.pass_context
def run(ctx: click.Context, once: bool) -> None:
    """Corre el monitoreo (en bucle por defecto)."""
    config = load_products_file(ctx.obj["products_file"])
    with StateStore(DEFAULT_DB_PATH) as store:
        if once:
            run_once(config, store)
        else:
            run_forever(config, store)


@main.command(name="list")
@click.pass_context
def list_products(ctx: click.Context) -> None:
    """Lista los productos configurados."""
    config = load_products_file(ctx.obj["products_file"])
    if not config.products:
        click.echo("No hay productos configurados.")
        return
    for product in config.products:
        target = f"${product.target_price:,.2f}" if product.target_price is not None else "sin definir"
        click.echo(f"- {product.nickname}: {product.url} (precio objetivo: {target})")


@main.command()
@click.argument("url")
@click.option("--nickname", default=None, help="Nombre corto para identificar el producto.")
@click.option("--target-price", type=float, default=None, help="Precio objetivo en MXN.")
@click.pass_context
def add(ctx: click.Context, url: str, nickname: str | None, target_price: float | None) -> None:
    """Agrega un producto a la lista de monitoreo."""
    products_file: Path = ctx.obj["products_file"]
    if products_file.exists():
        config = load_products_file(products_file)
    else:
        config = AppConfig(poll_interval_seconds=600, products=[])

    if any(p.url == url for p in config.products):
        click.echo("Ese producto ya está en la lista.")
        return

    config.products.append(
        ProductConfig(url=url, nickname=nickname or url, target_price=target_price)
    )
    save_products_file(products_file, config)
    click.echo(f"Agregado: {nickname or url}")


if __name__ == "__main__":
    main()
