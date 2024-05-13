"""
A group of commands that leverage the rest of the functionality of opkvs to manage SSH credentials
"""

import re
import sys
import os
import shutil
import subprocess

import click

from lib.op import (
    get_item,
    set_item,
    clear_items,
    list_items,
    infer_selected_vault,
    infer_selected_vault_name,
    has_item,
    delete_item,
    get_vault_id,
    VaultNotFound,
)
from lib.cli import die
from lib.fs import file_get_text_contents, file_put_text_contents


def check_item_name(item_name):
    if item_name == "alias":
        return True
    if item_name == "host":
        return True
    if item_name == "port":
        return True
    if re.match(r"^users\.(.*?)\.password$", item_name):
        return True
    if re.match(r"^users\.(.*?)\.id_rsa$", item_name):
        return True
    if re.match(r"^users\.(.*?)\.ssh_passphrase$", item_name):
        return True
    return False


def check_vault_format(item_names):
    return all(check_item_name(item_name) for item_name in item_names)


def check_vault_setup(vault_id):
    return (
        has_item(vault_id, "alias")
        and has_item(vault_id, "host")
        and has_item(vault_id, "port")
    )


def get_users_from_item_list(item_list):
    user_regex = re.compile(r"^users\.(.*?)\.id_rsa$")
    users = []
    for item in item_list:
        m = user_regex.match(item)
        if m:
            users.append(m.group(1))
    return users


def has_user(vault_id, username):
    users = get_users_from_item_list(list_items(vault_id))
    return username in users


@click.group()
@click.option("--vault", type=str, default=None)
@click.pass_context
def handler(ctx, vault=None):
    ctx.ensure_object(dict)
    selected_vault = infer_selected_vault(vault)
    if selected_vault is None:
        die(
            """
Cannot infer selected vault for the project in the current working directory:
            
No config file (opkvs.json) in the current working directory or field 'vault_id' and 'vault_name' are not set.
Not vault was specified as a command line option
            """
        )
    ctx.obj["vault_id"] = selected_vault
    ctx.obj["vault_name"] = infer_selected_vault_name(vault)


@handler.command()
@click.pass_context
def get_host(ctx):
    vault_id = ctx.obj["vault_id"]
    sys.stdout.write(get_item(vault_id, "host"))


@handler.command()
@click.pass_context
def get_port(ctx):
    vault_id = ctx.obj["vault_id"]
    sys.stdout.write(get_item(vault_id, "port"))


@handler.command()
@click.pass_context
def get_alias(ctx):
    vault_id = ctx.obj["vault_id"]
    sys.stdout.write(get_item(vault_id, "alias"))


@handler.command()
@click.pass_context
@click.option("--host", type=str, required=True)
@click.option("--alias", type=str, required=False, default=None)
@click.option("--port", type=int, required=False, default=22)
def init(ctx, host, alias=None, port=22):
    vault_id = ctx.obj["vault_id"]
    vault_name = ctx.obj["vault_name"]
    if alias is None:
        alias = vault_name
    set_item(vault_id, "alias", alias)
    set_item(vault_id, "host", host)
    set_item(vault_id, "port", str(port))


@handler.command()
@click.pass_context
def check(ctx):
    vault_id = ctx.obj["vault_id"]
    if not check_vault_setup(vault_id):
        die(f"Vault '{vault_id}' is not setup correctly.")
    if not check_vault_format(list_items(vault_id)):
        die(f"Vault '{vault_id}' has unrecognized keys.")


@handler.command()
@click.pass_context
def reset(ctx):
    vault_id = ctx.obj["vault_id"]
    vault_name = ctx.obj["vault_name"]
    if click.confirm(
        f"Are you sure you want to reset (clear all items in) the vault '{vault_name}'?"
    ):
        clear_items(vault_id)


@handler.command()
@click.pass_context
def list_users(ctx):
    vault_id = ctx.obj["vault_id"]
    users = get_users_from_item_list(list_items(vault_id))
    print("\n".join(users))


@handler.command()
@click.pass_context
@click.argument("username", type=str)
# All data is loaded from files for security reasons and to prevent issues with sanitzation on the commands line
@click.option("--password-file", type=click.Path(exists=True), required=True)
@click.option("--ssh-passphrase-file", type=click.Path(exists=True), required=True)
@click.option("--identity-file", type=click.Path(exists=True), required=True)
def add_user(
    ctx,
    username,
    password_file,
    ssh_passphrase_file,
    identity_file,
):
    vault_id = ctx.obj["vault_id"]
    item_key_password = f"users.{username}.password"
    item_key_ssh_passphrase = f"users.{username}.ssh_passphrase"
    item_key_id_rsa = f"users.{username}.id_rsa"
    set_item(vault_id, item_key_password, file_get_text_contents(password_file))
    set_item(
        vault_id, item_key_ssh_passphrase, file_get_text_contents(ssh_passphrase_file)
    )
    set_item(vault_id, item_key_id_rsa, file_get_text_contents(identity_file))


@handler.command()
@click.pass_context
@click.argument("username", type=str)
def remove_user(ctx, username):
    vault_id = ctx.obj["vault_id"]
    vault_name = ctx.obj["vault_name"]
    if not has_user(vault_id, username):
        die(f"User '{username}' does not exist in vault '{vault_name}'")
    item_key_password = f"users.{username}.password"
    item_key_ssh_passphrase = f"users.{username}.ssh_passphrase"
    item_key_id_rsa = f"users.{username}.id_rsa"
    delete_item(vault_id, item_key_password)
    delete_item(vault_id, item_key_ssh_passphrase)
    delete_item(vault_id, item_key_id_rsa)


@handler.command()
@click.pass_context
@click.argument("username", type=str)
def get_user_ssh_passphrase(ctx, username):
    vault_id = ctx.obj["vault_id"]
    vault_name = ctx.obj["vault_name"]
    if not has_user(vault_id, username):
        die(f"User '{username}' does not exist in vault '{vault_name}'")
    item_key = f"users.{username}.ssh_passphrase"
    sys.stdout.write(get_item(vault_id, item_key))


@handler.command()
@click.pass_context
@click.argument("username", type=str)
def get_user_password(ctx, username):
    vault_id = ctx.obj["vault_id"]
    vault_name = ctx.obj["vault_name"]
    if not has_user(vault_id, username):
        die(f"User '{username}' does not exist in vault '{vault_name}'")
    item_key = f"users.{username}.password"
    sys.stdout.write(get_item(vault_id, item_key))


@handler.command()
@click.pass_context
@click.argument("username", type=str)
def get_user_id_rsa(ctx, username):
    vault_id = ctx.obj["vault_id"]
    vault_name = ctx.obj["vault_name"]
    if not has_user(vault_id, username):
        die(f"User '{username}' does not exist in vault '{vault_name}'")
    item_key = f"users.{username}.id_rsa"
    sys.stdout.write(get_item(vault_id, item_key))


def process_authorized_keys_text(contents):
    contents = contents.replace("\r\n", "\n")
    contents = contents.strip("")
    contents = re.sub(r"\n+", "\n", contents)
    return contents


@handler.command()
@click.pass_context
@click.argument("username", type=str)
@click.option("--file", type=str, required=False, default=None)
def set_user_authorized_keys(ctx, username, file):
    vault_id = ctx.obj["vault_id"]
    vault_name = ctx.obj["vault_name"]
    if not has_user(vault_id, username):
        die(f"User '{username}' does not exist in vault '{vault_name}'")
    item_key = f"users.{username}.authorized_keys"
    contents = None
    if file is not None:
        contents = file_get_text_contents(file)
    if contents is None:
        stdin_contents = sys.stdin.read()
        if stdin_contents:
            contents = stdin_contents
    if contents is None:
        die("No input. Either pipe into stdin or specify a file with `--file=<FILE>`")
    contents = process_authorized_keys_text(contents)
    set_item(vault_id, item_key, contents)


@handler.command()
@click.pass_context
@click.argument("username", type=str)
@click.option("--file", type=str, required=False, default=None)
def add_user_authorized_keys(ctx, username, file):
    vault_id = ctx.obj["vault_id"]
    vault_name = ctx.obj["vault_name"]
    if not has_user(vault_id, username):
        die(f"User '{username}' does not exist in vault '{vault_name}'")
    item_key = f"users.{username}.authorized_keys"
    contents = None
    if file is not None:
        contents = file_get_text_contents(file)
    if contents is None:
        stdin_contents = sys.stdin.read()
        if stdin_contents:
            contents = stdin_contents
    if contents is None:
        die("No input. Either pipe into stdin or specify a file with `--file=<FILE>`")
    existing_contents = get_item(vault_id, get_item)
    if existing_contents is None:
        existing_contents = ""
    existing_contents = process_authorized_keys_text(contents)
    new_contents = process_authorized_keys_text(contents)
    set_item(vault_id, item_key, "\n".join([existing_contents, new_contents]))


@handler.command()
@click.pass_context
@click.argument("username", type=str)
def get_user_authorized_keys(ctx, username):
    vault_id = ctx.obj["vault_id"]
    vault_name = ctx.obj["vault_name"]
    if not has_user(vault_id, username):
        die(f"User '{username}' does not exist in vault '{vault_name}'")
    item_key = f"users.{username}.authorized_keys"
    contents = get_item(vault_id, item_key)
    sys.stdout.write(contents)


@click.command()
@click.argument("vaults", nargs=-1, type=str)
def ssh_compile(vaults):

    try:

        home_dir = os.path.expanduser("~")

        if not os.path.exists(os.path.join(home_dir, ".ssh")):
            os.mkdir(os.path.join(home_dir, ".ssh"))

        if not os.path.exists(os.path.join(home_dir, ".ssh", ".opkvs", "identities")):
            os.makedirs(
                os.path.join(home_dir, ".ssh", ".opkvs", "identities"), exist_ok=True
            )

        entries = []

        for vault in vaults:

            vault_id = get_vault_id(vault)

            vault_alias = get_item(vault_id, "alias")
            vault_host = get_item(vault_id, "host")
            vault_port = int(get_item(vault_id, "port"))

            vault_user_identities_path = os.path.join(
                home_dir, ".ssh", ".opkvs", "identities", vault
            )

            if os.path.exists(vault_user_identities_path):
                shutil.rmtree(vault_user_identities_path)

            os.mkdir(vault_user_identities_path)

            users = get_users_from_item_list(list_items(vault))

            for user in users:
                id_rsa = get_item(vault, f"users.{user}.id_rsa")
                os.mkdir(os.path.join(vault_user_identities_path, user))
                file_put_text_contents(
                    os.path.join(vault_user_identities_path, user, "id_rsa"), id_rsa
                )
                if os.name != "nt":

                    subprocess.check_output(
                        [
                            "sudo",
                            "chmod",
                            "600",
                            os.path.join(vault_user_identities_path, user, "id_rsa"),
                        ]
                    )

                full_alias = f"{vault_alias} | {user}{'' if vault_port == 22 else ' | ' + str(vault_port)}"
                entry = {}

                # entry["Host"] = full_alias
                entry["Host"] = vault
                entry["HostName"] = vault_host
                entry["User"] = user
                entry["IdentityFile"] = os.path.join(
                    vault_user_identities_path, user, "id_rsa"
                )
                entry["Port"] = vault_port

                entries.append(entry)

        def format_entry(entry):
            return f"""
Host "{entry['Host']}"
  HostName "{entry['HostName']}"
  User "{entry['User']}"
  IdentityFile "{entry['IdentityFile']}"
  Port "{entry['Port']}"
  ForwardX11 yes
""".strip()

        text = "\n\n".join([format_entry(entry) for entry in entries])

        print(text)

    except VaultNotFound as e:
        die(str(e))
