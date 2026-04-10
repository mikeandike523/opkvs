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
from lib.fs import file_get_text_contents
from lib.ssh_config import parse_ssh_config, apply_entries, serialize_config


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


def _is_windows_host():
    """
    Returns True when the process is running on a Windows host, regardless of
    whether the shell is cmd/PowerShell, Git Bash (MSYS2), or Cygwin.
    Git Bash sets os.name to 'posix', so we also check Windows-specific
    environment variables that are always present on Windows but absent in WSL.
    """
    if os.name == "nt":
        return True
    # WINDIR and OS=Windows_NT are set by Windows itself and inherited by Git Bash
    if os.environ.get("WINDIR") or os.environ.get("OS") == "Windows_NT":
        return True
    return False


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
# We allow user to specify,
# since in some cases user may run this from wsl,
# and want to first manage wsl ssh config and then windows ssh config
@click.option(
    "--target-os",
    type=click.Choice(["windows", "posix"]),
    required=False,
    default=None,
)
@click.option(
    "--windows-user-home",
    type=str,
    required=False,
    default=None,
)
@click.option(
    "--write", "-w",
    is_flag=True,
    default=False,
    help="Write entries directly into ~/.ssh/config instead of printing to stdout.",
)
@click.argument("vaults", nargs=-1, type=str)
def ssh_compile(target_os, windows_user_home, write, vaults):
    if target_os is None:
        target_os = "windows" if _is_windows_host() else "posix"
    if target_os == "windows" and not _is_windows_host() and windows_user_home is None:
        die(
            "`--windows-user-home` must be specified targeting windows from wsl or other posix compliant guest system"
        )
    try:

        home_dir = os.path.expanduser("~")

        if not _is_windows_host() and target_os == "windows":
            windows_user_home = windows_user_home.replace("\\", "/")
            windows_user_home = windows_user_home.strip("/")
            windows_user_home = re.sub(r"/+", "/", windows_user_home)
            components = windows_user_home.split("/")
            components[0] = components[0][:-1].lower()
            windows_user_home = "/".join(components)
            windows_user_home = f"/mnt/" + windows_user_home
            home_dir = windows_user_home

        if not os.path.exists(os.path.join(home_dir, ".ssh")):
            os.mkdir(os.path.join(home_dir, ".ssh"))

        if not os.path.exists(os.path.join(home_dir, ".ssh", ".opkvs", "identities")):
            os.makedirs(
                os.path.join(home_dir, ".ssh", ".opkvs", "identities"), exist_ok=True
            )

        entries = []

        for vault in vaults:

            vault_id = get_vault_id(vault)

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

                entry = {}

                if target_os == "posix":

                    entry["IdentityFile"] = os.path.join(
                        vault_user_identities_path, user, "id_rsa"
                    )

                    subprocess.check_output(
                        [
                            "sudo",
                            "chmod",
                            "600",
                            os.path.join(vault_user_identities_path, user, "id_rsa"),
                        ]
                    )

                else:
                    if _is_windows_host():
                        # Git Bash or native Windows — path is already a Windows path
                        win_id_rsa_filepath = os.path.join(
                            vault_user_identities_path, user, "id_rsa"
                        ).replace("/", "\\")
                    else:
                        # WSL targeting Windows — convert /mnt/<drive>/... to <DRIVE>:\...
                        win_id_rsa_filepath = os.path.join(
                            vault_user_identities_path, user, "id_rsa"
                        ).replace("/", "\\")[len("/mnt/"):]
                        components = win_id_rsa_filepath.split("\\")
                        components[0] = components[0].upper() + ":"
                        win_id_rsa_filepath = "\\".join(components)

                    entry["IdentityFile"] = win_id_rsa_filepath

                    # Attempt to restrict permissions using icacls (built into all Windows versions).
                    # From WSL we call icacls.exe; from Git Bash or native Windows we call icacls.
                    icacls = "icacls" if _is_windows_host() else "icacls.exe"
                    win_username = (
                        os.environ.get("USERNAME")
                        or os.environ.get("LOGNAME")
                        or os.environ.get("USER")
                        or ""
                    )
                    try:
                        subprocess.check_output(
                            [
                                icacls,
                                win_id_rsa_filepath,
                                "/inheritance:r",
                                "/grant:r",
                                f"{win_username}:(R)",
                            ],
                            stderr=subprocess.STDOUT,
                        )
                    except Exception:
                        sys.stderr.write(
                            f"Warning: Could not automatically set permissions on '{win_id_rsa_filepath}'.\n"
                            "Please restrict access manually: right-click the file > Properties > Security,\n"
                            "and ensure only your user account has access.\n"
                        )

                entry["Host"] = f"{user}@{vault}"
                entry["HostName"] = vault_host
                entry["User"] = user

                entry["Port"] = vault_port

                entries.append(entry)

        def ssh_quote(value, is_host_pattern=False):
            """
            Sanitize a value for safe embedding in a quoted ssh_config field.

            SSH config has no escape sequence for embedded double-quotes, so we
            strip them outright.  For Host pattern fields we also strip the glob
            characters (* ? !) that OpenSSH treats as special.
            """
            value = str(value).replace('"', '')
            if is_host_pattern:
                value = value.replace('*', '').replace('?', '')
                # A leading '!' means negation in a Host pattern — strip it
                value = value.lstrip('!')
            return value

        def format_entry(entry):
            return f"""
Host "{ssh_quote(entry['Host'], is_host_pattern=True)}"
  HostName "{ssh_quote(entry['HostName'])}"
  User "{ssh_quote(entry['User'])}"
  IdentityFile "{ssh_quote(entry['IdentityFile'])}"
  Port "{ssh_quote(entry['Port'])}"
  ForwardX11 yes
""".strip()

        formatted_blocks = [format_entry(entry) for entry in entries]
        host_aliases = [entry["Host"] for entry in entries]

        if not write:
            print("\n\n".join(formatted_blocks))
        else:
            ssh_config_path = os.path.join(home_dir, ".ssh", "config")

            try:
                existing_text = file_get_text_contents(ssh_config_path)
            except FileNotFoundError:
                existing_text = ""
            except PermissionError as exc:
                die(f"Cannot read {ssh_config_path}: {exc}")

            parsed = parse_ssh_config(existing_text)
            updated, actions = apply_entries(parsed, formatted_blocks, host_aliases)
            output_text = serialize_config(updated)

            try:
                # Write via a temp file so the config is never left half-written
                tmp_path = ssh_config_path + ".opkvs_tmp"
                with open(tmp_path, "w", newline="", encoding="utf-8") as f:
                    f.write(output_text)
                os.replace(tmp_path, ssh_config_path)
            except PermissionError as exc:
                die(f"Cannot write {ssh_config_path}: {exc}")

            for alias, action in actions:
                sys.stderr.write(f"  {action}: {alias}\n")

    except VaultNotFound as e:
        die(str(e))
