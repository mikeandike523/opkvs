# optkvs

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

## Requirements

@todo

## Installation

@todo

## Usage
   
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