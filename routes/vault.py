import subprocess
import json

import click
import pandas as pd

from lib.cli import die
from lib.op import get_vault_id, VaultNotFound


@click.group()
def handler():
    pass


def get_vault_list():
    as_list = json.loads(
        subprocess.check_output(["op", "vault", "list", "--format=json"]).decode(
            "utf-8"
        )
    )
    return as_list


@handler.command()
@click.option("--format", default="table", type=click.Choice(["json", "table"]))
def list(format):
    vault_list = get_vault_list()
    if format == "json":
        print(json.dumps(vault_list, indent=2))
    elif format == "table":
        df = pd.DataFrame.from_records(vault_list)
        print(df)


@handler.command()
@click.argument("name", required=True, type=str)
@click.option("--exact", default=False, is_flag=True)
def get_id(name, exact):
    try:
        print(get_vault_id(name, exact))
    except VaultNotFound as e:
        die(e.get_message())
