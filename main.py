import os
import web3
import requests
import eth_account
import eth_account.messages

MFR_DEVICE_SEEN_PRIV = 6

# These are dev numbers.
CLIENT_ID = "0x27950d45E810f34EA435B2da311e9e8306465Be0"
REDIRECT_URI = "https://elffjs.org"
SIGNER_PRIVATE_KEY = os.environ["SIGNER_PRIVATE_KEY"]
MFR_NFT_ADDR = "0xA4ad0F9c722588910791A9BAC63ADbB365614Bc7"
MFR_TOKEN_ID = 146
DEVICE_TOKEN_ID = 48

w3 = web3.Web3()

# Ask for the challenge to sign. Note that we are logging in "as" (the address field)
# the developer license address (also known as the developer license client id).
resp = requests.post(
    "https://auth.dev.dimo.zone/auth/web3/generate_challenge",
    params={
        "client_id": CLIENT_ID,
        "domain": REDIRECT_URI,
        "scope": "openid email",
        "response_type": "code",
        "address": CLIENT_ID,
    })

resp_body = resp.json()

challenge = resp_body["challenge"]

message = eth_account.messages.encode_defunct(text=challenge)

# Sign the challenge with a signer attached to the developer license.
signature = w3.eth.account.sign_message(message, SIGNER_PRIVATE_KEY).signature.to_0x_hex()

# Send the challenge back.
resp = requests.post(
    "https://auth.dev.dimo.zone/auth/web3/submit_challenge",
    data={
        "client_id": CLIENT_ID,
        "domain": REDIRECT_URI,
        "grant_type": "authorization_code",
        "state": resp_body["state"],
        "signature": signature,
    })

# The subject of this token is the developer license address.
access_token = resp.json()["access_token"]

# Swap that token for a token with the "device last seen" privilege (number 6)
# on the manufacturer. This must have been previously been granted to the developer
# license address.
resp = requests.post(
    "https://token-exchange-api.dev.dimo.zone/v1/tokens/exchange",
    json={
        "nftContractAddress": MFR_NFT_ADDR,
        "tokenId": MFR_TOKEN_ID,
        "privileges": [MFR_DEVICE_SEEN_PRIV]
    },
    headers={"Authorization": "Bearer " + access_token})

priv_token = resp.json()["token"]

# Note that with aliases and some admittedly ugly string manipulation we can query for
# several different devices at once.
# https://graphql.org/learn/queries/#aliases
query = """
query DeviceLastSeen($tokenId: Int!) {
    deviceActivity(by: {tokenId: $tokenId}) {
        lastActive
    }
}
"""

resp = requests.post(
    "https://telemetry-api.dev.dimo.zone/query",
    json={
        "query": query,
        "variables": {"tokenId": DEVICE_TOKEN_ID}
    },
    headers={"Authorization": "Bearer " + priv_token})

print(resp.json())