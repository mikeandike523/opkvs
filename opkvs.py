"""
A simple CLI tool to implement a key-value credential store powered by 1password
"""

import subprocess
import json
import sys

import click
import termcolor

from lib.op import (
    get_vault_id,
    VaultNotFound,
    run_op_command,
    obtain_secure_note_id_by_name,
    create_new_secure_note_with_name_and_content,
    update_secure_note_by_name,
    delete_secure_note_by_name,
    get_secure_note_content_by_id,
    upsert_secure_note_by_name,
)
from lib.config import Config
from lib.cli import die, warn

from routes.vault import handler as route_vault
from routes.config import handler as route_config


def infer_selected_vault(explicit_vault_name=None, exact=False):
    try:
        if explicit_vault_name:
            return get_vault_id(explicit_vault_name, exact)
        else:
            vid = Config.get("vault_id", None)
            vname = Config.get("vault_name", None)
            if vid:
                return vid
            if vname:
                return get_vault_id(vname, exact)
            return None

    except VaultNotFound as e:
        die(e.get_message())


@click.group()
def cli():
    pass


@cli.command()
@click.argument("key", type=str)
@click.option("-s", "--silent", is_flag=True, default=False)
@click.option("--vault", type=str, default=None)
@click.option("--exact", is_flag=True, default=False)
def get_item(key, silent=False, vault=None, exact=False):
    vault_id = infer_selected_vault(vault, exact)
    if vault_id is None:
        die(
            """
Cannot infer selected vault for the project in the current working directory:         
No config file (opkvs.json) in the current working directory or field 'vault_id' and 'vault_name' are not set.
Not vault was specified as a command line option
"""
        )
    note_id = obtain_secure_note_id_by_name(vault_id, key)
    if not note_id:
        warn(f"No item with key '{key}' found in vault '{vault_id}'", silent)
        return
    contents = get_secure_note_content_by_id(vault_id, note_id)
    sys.stdout.write(contents)


def upsert_content_procedure(key, value, silent=False, vault=None, exact=False):
    vault_id = infer_selected_vault(vault, exact)
    if vault_id is None:
        die(
            """
Cannot infer selected vault for the project in the current working directory:
            
No config file (opkvs.json) in the current working directory or field 'vault_id' and 'vault_name' are not set.
Not vault was specified as a command line option
"""
        )
    is_creating_new = upsert_secure_note_by_name(vault_id, key, value)
    if not silent:
        if is_creating_new:
            print("Creating new item with the specified content...")
        else:
            print("Updating existing item with the specified content...")


@cli.command()
@click.argument("key", type=str)
@click.argument("value", type=str)
@click.option("-s", "--silent", is_flag=True, default=False)
@click.option("--vault", type=str, default=None)
@click.option("--exact", is_flag=True, default=False)
def set_item(
    key,
    value,
    silent=False,
    vault=None,
    exact=False,
):
    upsert_content_procedure(key, value, silent, vault, exact)


@cli.command()
@click.argument("key", type=str)
@click.argument("filename", type=click.Path(exists=True))
@click.option("-s", "--silent", is_flag=True, default=False)
@click.option("--vault", type=str, default=None)
@click.option("--exact", is_flag=True, default=False)
def set_item_from_file(key, filename, silent=False, vault=None, exact=False):
    with open(filename, "r", encoding="utf-8") as f:
        value = f.read()
    upsert_content_procedure(key, value, silent, vault, exact)


@cli.command()
@click.argument("key", type=str)
@click.option("-s", "--silent", is_flag=True, default=False)
@click.option("--vault", type=str, default=None)
@click.option("--exact", is_flag=True, default=False)
def set_item_from_stdin(key, silent=False, vault=None, exact=False):
    value = sys.stdin.read()
    upsert_content_procedure(key, value, silent, vault, exact)


@cli.command()
@click.argument("key", type=str)
@click.option("-y", "--yes", is_flag=True, default=False)
@click.option("-s", "--silent", is_flag=True, default=False)
@click.option("--vault", type=str, default=None)
@click.option("--exact", is_flag=True, default=False)
def delete_item(
    key,
    yes=False,
    silent=False,
    vault=None,
    exact=False,
):
    vault_id = infer_selected_vault(vault, exact)
    if vault_id is None:
        die(
            """
Cannot infer selected vault for the project in the current working directory:
            
No config file (opkvs.json) in the current working directory or field 'vault_id' and 'vault_name' are not set.
Not vault was specified as a command line option
"""
        )
    note_id = obtain_secure_note_id_by_name(vault_id, key)
    if not note_id:
        warn(f"No item with key '{key}' found in vault '{vault_id}'", silent)
        return
    print("Successfully delete item with the specified key...")


cli.add_command(route_vault, "vault")
cli.add_command(route_config, "config")


if __name__ == "__main__":
    cli()
