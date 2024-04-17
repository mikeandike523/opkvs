import click

from lib.config import Config
from lib.op import get_vault_id, VaultNotFound
from lib.cli import die


@click.group()
def handler():
    pass


@handler.command()
@click.argument("name", required=True, type=str)
def set_vault(name):
    try:
        Config().set("vault_name", name)
    except VaultNotFound as e:
        die(e.get_message())
