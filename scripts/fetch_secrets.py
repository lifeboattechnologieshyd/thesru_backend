# import sys

# from azure.identity import DefaultAzureCredential
# from azure.keyvault.secrets import SecretClient


# def fetch_secrets(vault_name, service_name, output_file, at_output_file="at.env"):
#     """
#     Fetch secrets from Azure Key Vault and store them in environment files.

#     :param vault_name: Azure Key Vault name
#     :param service_name: Name of the service
#     :param output_file: Path to store all environment variables
#     :param at_output_file: Path to store specific AT env secrets (default: at.env)
#     """
#     # List of keys to store separately in at output file
#     at_env_keys = {}

#     # Create Azure Key Vault URL
#     key_vault_url = f"https://{vault_name}.vault.azure.net"

#     # Authenticate using Managed Identity / Environment Credentials
#     credential = DefaultAzureCredential()
#     client = SecretClient(vault_url=key_vault_url, credential=credential)

#     try:
#         # Retrieve all secrets from Key Vault
#         secrets = client.list_properties_of_secrets()
#         all_env_vars = {}
#         at_env_vars = {}

#         for secret in secrets:
#             secret_name = secret.name

#             # Only process secrets that start with the service prefix
#             if not secret_name or not secret_name.startswith(service_name):
#                 continue

#             secret_value = client.get_secret(secret_name).value

#             # remove service name prefix
#             formatted_name = secret_name[len(service_name) + 1 :]  # +1 for the tailing '-'

#             # Replace '-' with '_'
#             formatted_name = formatted_name.replace("-", "_")

#             all_env_vars[formatted_name] = secret_value

#             # Store separately if it's in at_env_keys
#             if formatted_name in at_env_keys:
#                 at_env_vars[formatted_name] = secret_value

#         # Write all secrets to output file
#         with open(output_file, "a") as env_file:
#             for key, value in all_env_vars.items():
#                 env_file.write(f"{key}={value}\n")

#         # Write AT-specific secrets to separate file
#         with open(at_output_file, "a") as at_env_file:
#             for key, value in at_env_vars.items():
#                 at_env_file.write(f"{key}={value}\n")

#         print(f"Secrets written to {output_file}")  # noqa: T201
#         print(f"AT environment secrets written to {at_output_file}")  # noqa: T201

#     except Exception as e:
#         print(f"Error fetching secrets: {e}", file=sys.stderr)  # noqa: T201
#         sys.exit(1)


# if __name__ == "__main__":
#     if len(sys.argv) < 4:
#         print(  # noqa: T201
#             "Usage: python fetch_keyvault_secrets.py <VAULT_NAME> <SERVICE_NAME> <OUTPUT_FILE> [AT_OUTPUT_FILE]",
#             file=sys.stderr,
#         )
#         sys.exit(1)

#     vault_name = sys.argv[1]
#     service_name = sys.argv[2]
#     output_file = sys.argv[3]
#     at_output_file = sys.argv[4] if len(sys.argv) > 4 else "at.env"

#     fetch_secrets(vault_name, service_name, output_file, at_output_file)
