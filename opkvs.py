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
)
from lib.config import Config
from lib.cli import die, warn

from routes.vault import handler as route_vault
from routes.config import handler as route_config


def infer_selected_vault(explicit_vault_name=None):
    try:
        if explicit_vault_name:
            return get_vault_id(explicit_vault_name)
        else:
            vname = Config().get("vault_name", None)
            if vname:
                return get_vault_id(vname)
            return None

    except VaultNotFound as e:
        die(str(e))


@click.group()
def cli():
    """
    A comprehensive command line interface for an encrypted and cloud-synced key-value store
    Allows services like 1password to in part like more code-friendly services like HashiCorp Vault or bitwarden,
    i.e. programmatic handling of application credentials

    This tool is useful for teams with mixed personal and applicaiton credentials, such as email credentials (accessed in the type manner)
    and api keys (command line automation)

    A company owner or team lead should dedicate individual vaults to each key value store, which will typically be one-per-project,
    and then keep personal credentials (such as email passwords) in a separate vault (e.g. "Employee Email Logins")


    For instance, the following may be the list of the vaults in a 1password business account

    1. Employee Email Logins (typical use)
    2. Employee Timesheet Logins (typical use)
    3. production_vps_credentials (opkvs keystore)
    4. myapp1 (opkvs keystore) (contains api keys and database credentials)
    5. myapp2 (opkvs keystore) (contains api keys and database credentials)
    6. mymobileapp1 (opkvs keystore) (contains api keys and database credentials)

    How you stay organized is up to you,
    for instance you may want to have a seperate 1password account for each team, instead of one for the entire organzation

    Keys in the store should generally by cli-safe identifiers, such as:

        For a project:

        development.database-password
        development.api-key
        staging.database-password
        staging.api-key
        production.database-password
        production.api-key

        For managing a vps:

        users.firstname_lastname.ssh_key
        users.firstname_lastname.ssh_passphrase
        users.firstname_lastname.username
        users.firstname_lastname.password


        Usage:
        (use `opkvs <SUBCOMMAND> --help` for more information about a specific subcommand)

            `opkvs config set-vault <VAULT_NAME> [--exact]`
            Edits the config file (opkvs.json) in the current working directory to default to using a vault named <VAULT_NAME>
            Creates the file it does not already exist
            Also identifies the vault id using the 1password cli
            If '--exact' is specified, the lookup will be case sensitive`

            `opkvs list-items [--vault=<VAULT_NAME>] [--exact]`
            Lists all (opkvs) items in the selected vault
            If --vault is not specified, it searches for the vault in the config file
            * If items not generated/managed by opkvs are present, they may break up opkvs entirely
              avoid manually adding, editing, or removing data from vaults managed by optkvs

            `opkvs set-item <KEY> <VALUE> [--vault=<VAULT_NAME>] [--exact]`
            Upserts an item into the selected vault with key <KEY> and value <VALUE>
            If --vault is not specified, it searches for the vault in the config file
            * It is recommended to use the config file, see `opkvs config set-vault <VAULT_NAME> [--exact]`

            `opkvs set-item <KEY> --file <FILE> [--vault=<VAULT_NAME>] [--exact]`
            Upserts an item into the selected vault with key <KEY> and value read from the file <FILE>
            The file must be ascii or utf-8 encoded text
            If --vault is not specified, it searches for the vault in the config file
            * It is recommended to use the config file, see `opkvs config set-vault <VAULT_NAME> [--exact]`

            `<PIPED DATA> | opkvs set-item <KEY> [--vault=<VAULT_NAME>] [--exact]`
            Upserts an item into the selected vault with key <KEY> and value read from stdin
            Stdin must be valid ascii or utf-8 encoded text
            If --vault is not specified, it searches for the vault in the config file
            * It is recommended to use the config file, see `opkvs config set-vault <VAULT_NAME> [--exact]`

            `opkvs get-item <KEY> [--vault=<VAULT_NAME>] [--exact]`
            Retrieve an item from the selected vault with key <KEY>
            If --vault is not specified, it searches for the vault in the config file
            * It is recommended to use the config file, see `opkvs config set-vault <VAULT_NAME> [--exact]`

            opkvs delete-item <KEY> [--vault=<VAULT_NAME>] [--exact]`
            Deletes an item from the selected vault with key <KEY>
            If --vault is not specified, it searches for the vault in the config file
            * It is recommended to use the config file, see `opkvs config set-vault <VAULT_NAME> [--exact]`

    """


@cli.command()
@click.argument("key", type=str)
@click.option("-s", "--silent", is_flag=True, default=False)
@click.option("--vault", type=str, default=None)
def get_item(key, silent=False, vault=None):
    vault_id = infer_selected_vault(vault)
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


def upsert_content_procedure(key, value, silent=False, vault=None):
    vault_id = infer_selected_vault(vault)
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
@click.argument("value", type=str, required=False, default=None)
@click.option("--file", type=click.Path(exists=True), required=False, default=None)
@click.option("-s", "--silent", is_flag=True, default=False)
@click.option("--vault", type=str, default=None)
def set_item(key, value, file, silent=False, vault=None):

    # just to handle terminals that might have some funny piping related behavior
    # only even attempt to read stdin if no other input was provided
    # otherwise for the calculation of the number of significant inputs, set it to None
    # so it will not be an undeclared variable
    stdin_value = None
    if value is None and file is None:
        stdin_value = sys.stdin.read().decode("utf-8")
        if len(stdin_value) == 0:
            stdin_value = value
        if file:
            with open(file, "r", encoding="utf-8") as f:
                file_value = f.read()
    contents = (
        value
        if value is not None
        else (file_value if file_value is not None else stdin_value)
    )

    num_significant = len(
        list(filter(lambda x: x is not None, [value, file_value, stdin_value]))
    )

    if num_significant == 0:
        die(
            f"""
No input was provided (no value, no file, no piped input).
"""
        )

    if num_significant > 1:
        die(
            """
Only specify one of the following:

- value
- file (using --file)
- piped input (using stdin)

            """
        )

    upsert_content_procedure(key, contents, silent, vault)


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
    if not yes:
        if not click.confirm(f"Are you sure you want to delete item with key '{key}'?"):
            return
    delete_secure_note_by_name(vault_id, key)
    print("Successfully delete item with the specified key...")


@cli.command()
@click.option("--vault", type=str, default=None)
def list_items(vault=None):
    vault_id = infer_selected_vault(vault)
    if vault_id is None:
        die(
            """
Cannot infer selected vault for the project in the current working directory:
            
No config file (opkvs.json) in the current working directory or field 'vault_id' and 'vault_name' are not set.
Not vault was specified as a command line option
"""
        )
    names_and_ids = list_all_secure_note_names_and_ids(vault_id)
    for name, _ in names_and_ids:
        print(name)


cli.add_command(route_vault, "vault")
cli.add_command(route_config, "config")


if __name__ == "__main__":
    cli()
