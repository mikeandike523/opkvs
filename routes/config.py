import click

from lib.config import Config
from lib.op import get_vault_id, VaultNotFound
from lib.cli import die

@click.group()
def handler():
    pass

@handler.command()
@click.argument("name", required=True, type=str)
@click.option("--exact", default=False, is_flag=True)
def set_vault(name, exact):
    try:
        Config().set("vault_name", 
                        name
                    ).set(
                    "vault_id",
                    get_vault_id(name, exact)
                    )
    except VaultNotFound as e:
        die(e.get_message())
