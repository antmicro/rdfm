import traceback
import requests
import argparse
import sys
import urllib.parse
import rdfm.api.auth
import rdfm.config
import rdfm.commands.devices
import rdfm.commands.packages
import rdfm.commands.groups
import rdfm.commands.permissions
from authlib.integrations.requests_client import OAuthError


def main():
    parser = argparse.ArgumentParser(
        description="RDFM Manager utility",
        prog="rdfm-mgmt",
        usage="rdfm-mgmt",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--url",
        type=str,
        default="http://127.0.0.1:5000/",
        help="URL to the RDFM Server",
    )
    parser.add_argument(
        "--cert",
        type=str,
        default="./certs/CA.crt",
        help="path to the server CA certificate used for establishing an HTTPS connection",     # noqa: E501
    )
    parser.add_argument(
        "--no-api-auth",
        default=False,
        action="store_true",
        dest="disable_api_auth",
        help="disable OAuth2 authentication for API requests",
    )

    subparsers = parser.add_subparsers(
        required=True, title="available commands"
    )
    # Add all subparsers for the different subcommands
    rdfm.commands.devices.add_devices_parser(subparsers)
    rdfm.commands.packages.add_packages_parser(subparsers)
    rdfm.commands.groups.add_groups_parser(subparsers)
    rdfm.commands.permissions.add_permissions_parser(subparsers)
    # Wrap argv so when no arguments are passed, we inject a help screen
    wrapped_args = None if sys.argv[1:] else ["--help"]
    args = parser.parse_args(args=wrapped_args)

    # Extract the configuration from the CLI arguments
    # In the future, we could also load some defaults from a
    # predefined config file here.
    config = rdfm.config.Config()
    config.server_url = args.url
    # Require the CA cert only when using HTTPS
    if urllib.parse.urlparse(config.server_url).scheme == "https":
        config.ca_cert = args.cert
    else:
        config.ca_cert = None
    config.disable_api_auth = args.disable_api_auth

    try:
        rdfm.config.load_auth_from_file(config)
        config.authorizer = rdfm.api.auth.create_authorizer(config)

        # Dispatch to the correct handler
        # We should pass the following arguments to the handler:
        #   - Config structure
        #   - parsed arguments from `argparser`
        # The handler optionally returns a string with a friendly user message
        ret = args.func(config, args)
        if ret is not None:
            print("rdfm-mgmt:", ret)
            exit(1)
    except requests.ConnectionError as e:
        print("rdfm-mgmt: Connection to the server failed:", e)
        exit(1)
    except requests.Timeout as e:
        print("rdfm-mgmt: Server request timed out:", e)
        exit(1)
    except OAuthError as e:
        print(
            "rdfm-mgmt: Invalid credentials were supplied for authorization, "
            "please check configuration."
        )
        print("OAuth error occurred:", e)
        exit(1)
    except RuntimeError as e:
        print("rdfm-mgmt:", e)
        exit(1)
    except Exception:
        traceback.print_exc()
        print("rdfm-mgmt: Unhandled exception!")
        exit(1)


if __name__ == "__main__":
    main()
