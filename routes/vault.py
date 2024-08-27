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
        subprocess.check_output(
            ["op", "vault", "list", "--format=json"], stdin=subprocess.DEVNULL
        ).decode("utf-8")
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
def get_id(name):
    try:
        print(get_vault_id(name))
    except VaultNotFound as e:
        die(e.get_message())
