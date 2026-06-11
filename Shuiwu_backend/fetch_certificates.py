# -*- coding: utf-8 -*-
"""
Fetch WeChat Pay Platform Certificates
"""
import os
import json
import time
import uuid
import hashlib
import base64
import requests
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend

# Configuration
MCHID = os.getenv("WECHAT_PAY_MCHID", "1738747799")
PRIVATE_KEY_PATH = os.getenv("WECHAT_PAY_PRIVATE_KEY_PATH", "./certs/apiclient_key_pkcs8.pem.bak")
API_URL = "https://api.mch.weixin.qq.com/v3/certificates"


def load_private_key(private_key_path: str):
    """Load merchant private key"""
    with open(private_key_path, 'rb') as f:
        private_key = serialization.load_pem_private_key(
            f.read(),
            password=None,
            backend=default_backend()
        )
    return private_key


def build_signature(timestamp: str, nonce_str: str, method: str, url: str) -> str:
    """Build signature string"""
    # Format: METHOD\nURL\nTimestamp\nNonce\nBody\n
    # For GET request, body is empty
    message = f"{method}\n{url}\n{timestamp}\n{nonce_str}\n\n"

    # SHA256 hash
    message_hash = hashlib.sha256(message.encode('utf-8')).digest()
    return message


def sign(message: str, private_key) -> str:
    """Sign with private key"""
    message_bytes = message.encode('utf-8')
    message_hash = hashlib.sha256(message_bytes).digest()
    signature = private_key.sign(
        message_hash,
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode('utf-8')


def build_authorization(timestamp: str, nonce_str: str, signature: str) -> str:
    """Build Authorization header"""
    return f'WECHATPAY2-SHA256-RSA2048 mchid="{MCHID}",nonce_str="{nonce_str}",timestamp="{timestamp}",signature="{signature}"'


def get_certificates():
    """Fetch platform certificate list"""
    print("=" * 60)
    print("WeChat Pay Platform Certificate Fetcher")
    print("=" * 60)
    print(f"Merchant ID: {MCHID}")
    print(f"Private Key: {PRIVATE_KEY_PATH}")
    print(f"API URL: {API_URL}")
    print("=" * 60)

    # Load private key
    try:
        private_key = load_private_key(PRIVATE_KEY_PATH)
        print("[OK] Private key loaded successfully")
    except Exception as e:
        print(f"[FAIL] Failed to load private key: {e}")
        return

    # Generate timestamp and nonce
    timestamp = str(int(time.time()))
    nonce_str = uuid.uuid4().hex[:32]

    # Build signature
    method = "GET"
    url = "/v3/certificates"
    message = build_signature(timestamp, nonce_str, method, url)

    # Sign
    signature = sign(message, private_key)

    # Build Authorization header
    authorization = build_authorization(timestamp, nonce_str, signature)

    # Request headers
    headers = {
        "Authorization": authorization,
        "Accept": "application/json",
    }

    print(f"\nSending request...")
    print(f" URL: {API_URL}")
    print(f" Method: {method}")
    print(f" Timestamp: {timestamp}")
    print(f"  Nonce: {nonce_str}")
    print(f"  Authorization: {authorization[:100]}...")
    print("=" * 60)

    # Send request
    try:
        response = requests.get(API_URL, headers=headers, timeout=30)
        print(f"\nResponse status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("\n[OK] Fetch successful!")
            print("=" * 60)

            # Parse response
            data = result.get("data", [])
            print(f"Available certificates: {len(data)}")
            print("=" * 60)

            for i, cert_info in enumerate(data, 1):
                print(f"\nCertificate #{i}:")
                print(f"  Serial No: {cert_info.get('serial_no')}")
                print(f"  Effective Time: {cert_info.get('effective_time')}")
                print(f"  Expire Time: {cert_info.get('expire_time')}")

                encrypt_cert = cert_info.get('encrypt_certificate', {})
                if encrypt_cert:
                    print(f"  Algorithm: {encrypt_cert.get('algorithm')}")
                    print(f"  Nonce: {encrypt_cert.get('nonce')[:20]}...")
                    print(f"  Associated Data: {encrypt_cert.get('associated_data')}")
                    print(f"  Ciphertext: {encrypt_cert.get('ciphertext')[:50]}...")

            # Save full JSON response
            output_file = "wechat_pay_certificates.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"\n" + "=" * 60)
            print(f"Full response saved to: {output_file}")
            print("=" * 60)

            return data
        else:
            print(f"\n[FAIL] Request failed")
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return None
    except Exception as e:
        print(f"\n[FAIL] Request exception: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    certificates = get_certificates()

    if certificates:
        print("\n" + "=" * 60)
        print("Next Steps:")
        print("=" * 60)
        print("1. Find the latest platform certificate (latest effective_time)")
        print("2. Extract the certificate and save to certs/pub_key.pem")
        print("3. The certificate content is in 'encrypt_certificate' field")
        print("=" * 60)
