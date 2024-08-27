import sys

import click

from lib.op import (
    get_vault_id,
    VaultNotFound,
    obtain_secure_note_id_by_name,
    delete_secure_note_by_name,
    get_secure_note_content_by_id,
    upsert_secure_note_by_name,
    list_all_secure_note_names_and_ids,
    infer_selected_vault,
)
from lib.config import Config
from lib.cli import die, warn

from routes.vault import handler as route_vault
from routes.config import handler as route_config
from routes.ssh import handler as route_ssh, ssh_compile


@click.group()
def cli():
    """
    A comprehensive command line interface for an encrypted
    and cloud-synced key-value store

    Allows services like 1password to in part like more code-friendly services
    like HashiCorp Vault or bitwarden,
    i.e. programmatic handling of application credentials

    This tool is useful for teams with mixed typical/personal
    and programmatic/applicaiton credentials,
    such as email (typical use) credentials and api keys (programatic use)

    Usage:

        opkvs [command] [options] [arguments]

        Get help with a particular command
        opkvs [command] --help

    See https://github.com/mikeandike523/opkvs/blob/main/README.md
    for detailed usage information.

    """


@cli.command()
@click.argument("key", type=str)
@click.option("-s", "--silent", is_flag=True, default=False)
@click.option("--vault", type=str, default=None)
def get_item(key, silent=False, vault=None):
    vault_id = infer_selected_vault(vault)
    note_id = obtain_secure_note_id_by_name(vault_id, key)
    if not note_id:
        warn(f"No item with key '{key}' found in vault '{vault_id}'", silent)
        return
    contents = get_secure_note_content_by_id(vault_id, note_id)
    sys.stdout.write(contents)


def upsert_content_procedure(key, value, silent=False, vault=None):
    vault_id = infer_selected_vault(vault)
    is_creating_new = upsert_secure_note_by_name(vault_id, key, value)
    if not silent:
        if is_creating_new:
            print("Creating new item with the specified content...")
        else:
            print("Updating existing item with the specified content...")


@cli.command()
@click.argument("key", type=str)
@click.argument("value", type=str, required=False, default=None)
@click.option("--file", type=click.Path(exists=True), required=False, default=None)
@click.option("-s", "--silent", is_flag=True, default=False)
@click.option("--vault", type=str, default=None)
def set_item(key, value=None, file=None, silent=False, vault=None):

    final_value = None

    stdin_value = sys.stdin.read().strip()
    if stdin_value:
        final_value = stdin_value

    if file:
        with open(file, "r", encoding="utf-8") as f:
            file_value = f.read().strip()
            if file_value:
                final_value = file_value

    upsert_content_procedure(key, final_value, silent, vault)


@cli.command()
@click.argument("key", type=str)
@click.option("-y", "--yes", is_flag=True, default=False)
@click.option("-s", "--silent", is_flag=True, default=False)
@click.option("--vault", type=str, default=None)
def delete_item(
    key,
    yes=False,
    silent=False,
    vault=None,
):
    vault_id = infer_selected_vault(vault)
    note_id = obtain_secure_note_id_by_name(vault_id, key)
    if not note_id:
        warn(f"No item with key '{key}' found in vault '{vault_id}'", silent)
        return
    if not yes:
        if not click.confirm(f"Are you sure you want to delete item with key '{key}'?"):
            return
    delete_secure_note_by_name(vault_id, key)
    print("Successfully delete item with the specified key...")


@cli.command()
@click.option("--vault", type=str, default=None)
def list_items(vault=None):
    vault_id = infer_selected_vault(vault)
    names_and_ids = list_all_secure_note_names_and_ids(vault_id)
    for name, _ in names_and_ids:
        print(name)


cli.add_command(route_vault, "vault")
cli.add_command(route_config, "config")
cli.add_command(route_ssh, "ssh")
cli.add_command(ssh_compile)


if __name__ == "__main__":
    cli()
