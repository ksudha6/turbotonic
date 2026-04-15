from __future__ import annotations

import os

from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers import bytes_to_base64url, base64url_to_bytes
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

RP_ID = os.environ.get("WEBAUTHN_RP_ID", "localhost")
RP_NAME = os.environ.get("WEBAUTHN_RP_NAME", "Turbo Tonic")
ORIGIN = os.environ.get("WEBAUTHN_ORIGIN", "http://localhost:5174")


def create_registration_options(
    user_id: str, username: str, display_name: str
) -> tuple[dict, bytes]:
    """Generate WebAuthn registration options.

    Returns (options_dict, challenge_bytes).
    """
    options = generate_registration_options(
        rp_id=RP_ID,
        rp_name=RP_NAME,
        user_id=user_id.encode(),
        user_name=username,
        user_display_name=display_name,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
    )
    # Convert to JSON-serializable dict
    options_dict = {
        "rp": {"id": options.rp.id, "name": options.rp.name},
        "user": {
            "id": bytes_to_base64url(options.user.id),
            "name": options.user.name,
            "displayName": options.user.display_name,
        },
        "challenge": bytes_to_base64url(options.challenge),
        "pubKeyCredParams": [
            {"type": p.type, "alg": p.alg} for p in options.pub_key_cred_params
        ],
        "timeout": options.timeout,
        "authenticatorSelection": {
            "residentKey": options.authenticator_selection.resident_key.value if options.authenticator_selection else "preferred",
            "userVerification": options.authenticator_selection.user_verification.value if options.authenticator_selection else "preferred",
        },
        "attestation": options.attestation.value if options.attestation else "none",
    }
    return options_dict, options.challenge


def verify_registration(
    credential_json: dict, challenge: bytes
) -> tuple[str, bytes, int]:
    """Verify a registration response from the browser.

    Returns (credential_id_base64url, public_key_bytes, sign_count).
    """
    verification = verify_registration_response(
        credential=credential_json,
        expected_challenge=challenge,
        expected_rp_id=RP_ID,
        expected_origin=ORIGIN,
    )
    return (
        bytes_to_base64url(verification.credential_id),
        verification.credential_public_key,
        verification.sign_count,
    )


def create_authentication_options(
    credentials: list[tuple[str, bytes]]
) -> tuple[dict, bytes]:
    """Generate WebAuthn authentication options.

    credentials: list of (credential_id_base64url, public_key_bytes)
    Returns (options_dict, challenge_bytes).
    """
    allow_credentials = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(cred_id))
        for cred_id, _ in credentials
    ]
    options = generate_authentication_options(
        rp_id=RP_ID,
        allow_credentials=allow_credentials,
        user_verification=UserVerificationRequirement.PREFERRED,
    )
    options_dict = {
        "challenge": bytes_to_base64url(options.challenge),
        "timeout": options.timeout,
        "rpId": options.rp_id,
        "allowCredentials": [
            {
                "type": c.type,
                "id": bytes_to_base64url(c.id),
            }
            for c in (options.allow_credentials or [])
        ],
        "userVerification": options.user_verification.value if options.user_verification else "preferred",
    }
    return options_dict, options.challenge


def verify_authentication(
    credential_json: dict,
    challenge: bytes,
    credential_public_key: bytes,
    credential_current_sign_count: int,
) -> int:
    """Verify an authentication response from the browser.

    Returns the new sign_count.
    """
    verification = verify_authentication_response(
        credential=credential_json,
        expected_challenge=challenge,
        expected_rp_id=RP_ID,
        expected_origin=ORIGIN,
        credential_public_key=credential_public_key,
        credential_current_sign_count=credential_current_sign_count,
    )
    return verification.new_sign_count
