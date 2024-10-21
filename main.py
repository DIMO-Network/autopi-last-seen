import os
import web3
import requests
import eth_account
import eth_account.messages

MFR_DEVICE_SEEN_PRIV = 6

CLIENT_ID = "0x97ECA5840C33Cd3563a3d2Ea0DA2d10259b113c9" # AutoPi developer license, token id 5.
REDIRECT_URI = "https://dimo.qa.autopi.io/#/fleetvehicles"
SIGNER_PRIVATE_KEY = os.environ["SIGNER_PRIVATE_KEY"]
MFR_NFT_ADDR = "0x3b07e2A2ABdd0A9B8F7878bdE6487c502164B9dd" # Prod address.
MFR_TOKEN_ID = 137 # AutoPi.
DEVICE_TOKEN_ID = 2080 # Malte's prod device.

w3 = web3.Web3()

# Ask for the challenge to sign. Note that we are logging in "as" (the address field)
# the developer license address (also known as the developer license client id).
resp = requests.post(
    "https://auth.dimo.zone/auth/web3/generate_challenge",
    params={
        "client_id": CLIENT_ID,
        "domain": REDIRECT_URI,
        "scope": "openid email",
        "response_type": "code",
        "address": CLIENT_ID,
    },
)

resp_body = resp.json()

challenge = resp_body["challenge"]

message = eth_account.messages.encode_defunct(text=challenge)

# Sign the challenge with a signer attached to the developer license.
signature = w3.eth.account.sign_message(
    message, SIGNER_PRIVATE_KEY
).signature.to_0x_hex()

# Send the challenge back.
resp = requests.post(
    "https://auth.dimo.zone/auth/web3/submit_challenge",
    data={
        "client_id": CLIENT_ID,
        "domain": REDIRECT_URI,
        "grant_type": "authorization_code",
        "state": resp_body["state"],
        "signature": signature,
    },
)

# The subject of this token is the developer license address.
access_token = resp.json()["access_token"]

# Swap that token for a token with the "device last seen" privilege (number 6)
# on the manufacturer. This must have been previously been granted to the developer
# license address.
resp = requests.post(
    "https://token-exchange-api.dimo.zone/v1/tokens/exchange",
    json={
        "nftContractAddress": MFR_NFT_ADDR,
        "tokenId": MFR_TOKEN_ID,
        "privileges": [MFR_DEVICE_SEEN_PRIV],
    },
    headers={"Authorization": "Bearer " + access_token},
)

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
    "https://telemetry-api.dimo.zone/query",
    json={"query": query, "variables": {"tokenId": DEVICE_TOKEN_ID}},
    headers={"Authorization": "Bearer " + priv_token},
)

last_active = resp.json()["data"]["deviceActivity"]["lastActive"]

print("Device with token id {} last active at {}".format(DEVICE_TOKEN_ID, last_active))
