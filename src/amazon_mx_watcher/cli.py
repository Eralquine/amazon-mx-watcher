from __future__ import annotations

import logging
from pathlib import Path

import click

from .config import (
    AppConfig,
    ProductConfig,
    SearchConfig,
    load_env,
    load_products_file,
    save_products_file,
)
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
    """Lista los productos y búsquedas configurados."""
    config = load_products_file(ctx.obj["products_file"])
    if not config.products and not config.searches:
        click.echo("No hay productos ni búsquedas configurados.")
        return
    for product in config.products:
        target = f"${product.target_price:,.2f}" if product.target_price is not None else "sin definir"
        click.echo(f"[producto] {product.nickname}: {product.url} (precio objetivo: {target})")
    for search in config.searches:
        max_price = f"${search.max_price:,.2f}" if search.max_price is not None else "sin definir"
        click.echo(
            f"[búsqueda] {search.nickname}: \"{search.query}\" "
            f"(palabras clave: {search.keywords or 'ninguna'}, precio máx.: {max_price})"
        )


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


@main.command(name="add-search")
@click.argument("query")
@click.option("--nickname", default=None, help="Nombre corto para identificar la búsqueda.")
@click.option(
    "--keyword",
    "keywords",
    multiple=True,
    help="Palabra que debe aparecer en el título del resultado (repetible).",
)
@click.option("--max-price", type=float, default=None, help="Precio máximo en MXN para notificar.")
@click.pass_context
def add_search(
    ctx: click.Context,
    query: str,
    nickname: str | None,
    keywords: tuple[str, ...],
    max_price: float | None,
) -> None:
    """Agrega una búsqueda para detectar productos que aún no existen como listado.

    Ejemplo: amazon-mx-watcher add-search "consola X edición limitada" --max-price 9000
    """
    products_file: Path = ctx.obj["products_file"]
    if products_file.exists():
        config = load_products_file(products_file)
    else:
        config = AppConfig(poll_interval_seconds=600, products=[])

    if any(s.query == query for s in config.searches):
        click.echo("Esa búsqueda ya está en la lista.")
        return

    config.searches.append(
        SearchConfig(
            query=query,
            nickname=nickname or query,
            keywords=[k.lower() for k in keywords],
            max_price=max_price,
        )
    )
    save_products_file(products_file, config)
    click.echo(f"Agregada búsqueda: {nickname or query}")


if __name__ == "__main__":
    main()
