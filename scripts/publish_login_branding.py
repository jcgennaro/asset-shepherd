"""Publish the checked-in logo/CSS to the existing Cognito classic app client only."""

# boto3 clients expose dynamically generated service methods.
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false

import argparse
import hashlib
import json
from pathlib import Path

import boto3


def main() -> None:
    """Preview by default; --apply authorizes the exact logo and CSS update."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", default="asset-shepherd-admin")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--stack", default="asset-shepherd-auth")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "infra" / "branding"
    css = (root / "cognito-classic.css").read_text(encoding="utf-8")
    logo = (root / "login-logo.png").read_bytes()
    if len(css.encode()) > 3072 or len(logo) > 100 * 1024:
        raise ValueError("Cognito classic CSS/logo payload exceeds the documented limits")
    if not logo.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("The branding logo must be a PNG")
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    stack = session.client("cloudformation").describe_stacks(StackName=args.stack)["Stacks"][0]
    outputs = {item["OutputKey"]: item["OutputValue"] for item in stack["Outputs"]}
    client = session.client("cognito-idp")
    domain = outputs["LoginDomain"].split("//", 1)[1].split(".", 1)[0]
    description = client.describe_user_pool_domain(Domain=domain)["DomainDescription"]
    if (
        description["UserPoolId"] != outputs["UserPoolId"]
        or description.get("ManagedLoginVersion", 1) != 1
    ):
        raise ValueError("Expected the existing classic login domain for this exact user pool")
    result = {
        "applied": args.apply,
        "stack": args.stack,
        "logo_sha256": hashlib.sha256(logo).hexdigest(),
        "css_sha256": hashlib.sha256(css.encode()).hexdigest(),
    }
    if args.apply:
        response = client.set_ui_customization(
            UserPoolId=outputs["UserPoolId"],
            ClientId=outputs["ClientId"],
            CSS=css,
            ImageFile=logo,
        )
        result["css_version"] = response["UICustomization"]["CSSVersion"]
    print(json.dumps(result))


if __name__ == "__main__":
    main()
