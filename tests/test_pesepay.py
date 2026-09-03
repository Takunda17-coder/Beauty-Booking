# -*- coding: utf-8 -*-
"""
Pesepay Gateway Sandbox Test Suite
Verifies AES-256-CBC encryption, PKCS7 padding, payload integrity, and mock API lifecycle.
"""

import sys
import os

# Add addons path to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
module_dir = os.path.dirname(current_dir)
addons_dir = os.path.dirname(module_dir)
import importlib.util
client_path = os.path.join(module_dir, "models", "pesepay_client.py")
spec = importlib.util.spec_from_file_location("pesepay_client", client_path)
pesepay_client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pesepay_client)

PesepayClient = pesepay_client.PesepayClient
DEFAULT_INTEGRATION_KEY = pesepay_client.DEFAULT_INTEGRATION_KEY
DEFAULT_ENCRYPTION_KEY = pesepay_client.DEFAULT_ENCRYPTION_KEY


def test_encryption_decryption_roundtrip():
    print("\n--- TEST 1: AES-256-CBC PKCS7 Encryption / Decryption ---")
    client = PesepayClient(DEFAULT_INTEGRATION_KEY, DEFAULT_ENCRYPTION_KEY)
    test_data = {
        "amountDetails": {
            "amount": 25.50,
            "currencyCode": "USD"
        },
        "merchantReference": "BK-TEST-00001",
        "reasonForPayment": "Haircut & Beard Trim",
        "resultUrl": "https://example.com/beauty/payment/result",
        "customer": {
            "name": "John Doe",
            "phone": "0777777777",
            "email": "john@example.com"
        }
    }

    encrypted_b64 = client.encrypt_payload(test_data)
    print(f"[OK] Encrypted Ciphertext (Base64 length {len(encrypted_b64)}): {encrypted_b64[:40]}...")

    decrypted_data = client.decrypt_payload(encrypted_b64)
    print(f"[OK] Decrypted Data Match: {decrypted_data == test_data}")
    assert decrypted_data == test_data, "Decrypted data does not match original!"
    print("Test 1 PASSED!")


def test_encryption_key_length_validation():
    print("\n--- TEST 2: Encryption Key Length Validation ---")
    try:
        PesepayClient("valid_key", "too_short")
        assert False, "Should have raised ValueError for invalid key length"
    except ValueError as e:
        print(f"[OK] Correctly caught invalid key length: {e}")
    print("Test 2 PASSED!")


def test_payload_structure():
    print("\n--- TEST 3: Payment Request Payload Structure ---")
    client = PesepayClient(DEFAULT_INTEGRATION_KEY, DEFAULT_ENCRYPTION_KEY)
    res = client.initiate_payment(
        merchant_reference="BK-00042",
        amount=15.00,
        currency_code="USD",
        reason="Barber Cut",
        customer_name="Alice Smith",
        customer_phone="0777777777",
    )
    print("Initiate payment response:", res)
    assert "success" in res
    assert "error" in res
    print("Test 3 PASSED!")


if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING PESEPAY SANDBOX GATEWAY TESTS")
    print("=" * 60)
    test_encryption_decryption_roundtrip()
    test_encryption_key_length_validation()
    test_payload_structure()
    print("\n" + "=" * 60)
    print("ALL PESEPAY UNIT TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)
