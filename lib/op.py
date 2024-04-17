import subprocess
import json
import tempfile
import os
from base64 import b64encode, b64decode

from lib.cli import die


class VaultNotFound(Exception):
    def __init__(self, name, exact):
        self.name = name
        self.exact = exact

    def get_message(self):
        qualification = "(case insensitive)" if not self.exact else ""
        return f"""
No vault named '{self.name}' {qualification}
Try `opkvs vault list` to see a list of available vaults
""".strip()


class NoteNotFound(Exception):
    pass


def get_vault_list():
    as_list = json.loads(
        subprocess.check_output(["op", "vault", "list", "--format=json"]).decode(
            "utf-8"
        )
    )
    return as_list


def get_vault_id(name, exact):
    vault_list = get_vault_list()
    for vault in vault_list:
        if exact:
            if vault["id"] == name:
                return vault["id"]
        else:
            if vault["name"].lower() == name.lower():
                return vault["id"]

    raise VaultNotFound(name, exact)


def run_op_command(args):
    p = subprocess.Popen(["op"] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = p.communicate()
    rc = p.returncode
    stdout = stdout.decode("utf-8") if stdout is not None else ""
    stderr = stderr.decode("utf-8") if stderr is not None else ""
    if rc != 0:
        die(
            f"""
Could not run op command:
stdout:
{stdout}
stderr:
{stderr}
"""
        )
    return stdout


def list_all_secure_note_names_and_ids(vault_id):
    output = run_op_command(
        [
            "item",
            "list",
            "--vault",
            vault_id,
            "--categories",
            "SecureNote",
            "--format=json",
        ]
    ).strip()
    if not output:
        return []
    notes = json.loads(output)
    return [(note["title"], note["id"]) for note in notes]


def obtain_secure_note_id_by_name(vault_id, note_name):
    all_notes_list = list_all_secure_note_names_and_ids(vault_id)
    for title, note_id in all_notes_list:
        if title == note_name:
            return note_id
    return None


def create_new_secure_note_with_name_and_content(vault_id, note_name, note_content):

    # Use the op command to create a secure note with content from the temporary file
    run_op_command(
        [
            "item",
            "create",
            f'value="{b64encode(note_content.encode("utf-8")).decode("utf-8")}"',
            "--category",
            "Secure Note",
            "--title",
            note_name,
            "--vault",
            vault_id,
        ]
    )


def update_secure_note_by_name(vault_id, note_name, note_content):
    note_id = obtain_secure_note_id_by_name(vault_id, note_name)
    if note_id is None:
        raise NoteNotFound(f"Secure note with name '{note_name}' not found.")

    run_op_command(
        [
            "item",
            "edit",
            note_id,
            f'value="{b64encode(note_content.encode("utf-8")).decode("utf-8")}"',
            "--vault",
            vault_id,
        ]
    )


def upsert_secure_note_by_name(vault_id, note_name, note_content):
    note_id = obtain_secure_note_id_by_name(vault_id, note_name)
    if note_id is not None:
        update_secure_note_by_name(vault_id, note_name, note_content)
        return False
    else:
        create_new_secure_note_with_name_and_content(vault_id, note_name, note_content)
        return True


def delete_secure_note_by_name(vault_id, note_name):
    note_id = obtain_secure_note_id_by_name(vault_id, note_name)
    if note_id is None:
        raise NoteNotFound(f"Secure note with name '{note_name}' not found.")

    # Run the delete command
    run_op_command(["item", "delete", note_id])


def get_secure_note_content_by_id(vault_id, note_id):
    if note_id is None:
        raise NoteNotFound("Secure note ID was not provided.")

    # Command to retrieve only the notes content from the secure note
    output = run_op_command(
        ["item", "get", note_id, "--vault", vault_id, "--fields", "value"]
    ).strip()[1:-1]

    # Process output to get the content of the notes directly
    note_content = b64decode(output.encode("utf-8")).decode("utf-8")
    return note_content
