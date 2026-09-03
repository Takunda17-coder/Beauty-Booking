# -*- coding: utf-8 -*-
"""
Pesepay Sandbox Payment Gateway Client
Handles AES-256-CBC encryption/decryption, API communication, and sandbox simulation
for EcoCash, OneMoney, and Visa/Mastercard payments.
"""

import base64
import json
import logging
import requests
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

_logger = logging.getLogger(__name__)

# Pesepay Sandbox & Production Base URLs
PESEPAY_SANDBOX_BASE_URL = "https://api.pesepay.com"
PESEPAY_MAKE_PAYMENT_PATH = "/api/payments-engine/v2/payments/make-payment"
PESEPAY_CHECK_PAYMENT_PATH = "/api/payments-engine/v1/payments/check-payment"

# Sandbox Default Credentials (can be overridden via ir.config_parameter)
DEFAULT_INTEGRATION_KEY = "4ef545a6-5260-40d5-ba80-93c5bdc7ea31"
DEFAULT_ENCRYPTION_KEY = "b9b9826ba47447f298fc0f565ff89907"  # 32 characters


class PesepayClient:
    """Client for communicating with the Pesepay Payment Gateway API."""

    def __init__(self, integration_key=None, encryption_key=None, base_url=None):
        self.integration_key = (integration_key or DEFAULT_INTEGRATION_KEY).strip()
        self.encryption_key = (encryption_key or DEFAULT_ENCRYPTION_KEY).strip()
        self.base_url = (base_url or PESEPAY_SANDBOX_BASE_URL).rstrip('/')

        if len(self.encryption_key) != 32:
            raise ValueError(
                f"Pesepay encryption key must be exactly 32 characters long. Current length: {len(self.encryption_key)}"
            )

    def encrypt_payload(self, data_dict):
        """Encrypts a dictionary into AES-256-CBC ciphertext (Base64).

        :param data_dict: Dict containing payment request data
        :return: Base64-encoded encrypted payload string
        """
        try:
            key_bytes = self.encryption_key.encode('utf-8')
            iv_bytes = self.encryption_key[:16].encode('utf-8')

            json_bytes = json.dumps(data_dict).encode('utf-8')

            # PKCS7 Padding for 128-bit block size
            padder = padding.PKCS7(128).padder()
            padded_data = padder.update(json_bytes) + padder.finalize()

            cipher = Cipher(algorithms.AES(key_bytes), modes.CBC(iv_bytes))
            encryptor = cipher.encryptor()
            encrypted_bytes = encryptor.update(padded_data) + encryptor.finalize()

            return base64.b64encode(encrypted_bytes).decode('utf-8')
        except Exception as exc:
            _logger.error("Pesepay encryption error: %s", str(exc))
            raise

    def decrypt_payload(self, encrypted_b64):
        """Decrypts an AES-256-CBC ciphertext (Base64) back to a Python dictionary.

        :param encrypted_b64: Base64-encoded encrypted payload string
        :return: Decrypted dictionary
        """
        try:
            key_bytes = self.encryption_key.encode('utf-8')
            iv_bytes = self.encryption_key[:16].encode('utf-8')

            raw_cipher = base64.b64decode(encrypted_b64)

            decryptor = Cipher(algorithms.AES(key_bytes), modes.CBC(iv_bytes)).decryptor()
            decrypted_padded = decryptor.update(raw_cipher) + decryptor.finalize()

            unpadder = padding.PKCS7(128).unpadder()
            unpadded_bytes = unpadder.update(decrypted_padded) + unpadder.finalize()

            return json.loads(unpadded_bytes.decode('utf-8'))
        except Exception as exc:
            _logger.error("Pesepay decryption error: %s", str(exc))
            raise

    def initiate_payment(
        self,
        merchant_reference,
        amount,
        currency_code="USD",
        reason="Beauty Service Appointment",
        result_url="https://example.com/beauty/payment/result",
        return_url="https://example.com/beauty/payment/result",
        customer_name=None,
        customer_phone=None,
        customer_email=None,
    ):
        """Initiates a payment request with Pesepay sandbox.

        :return: dict with keys: 'success', 'redirect_url', 'poll_url', 'reference_number', 'raw_response', 'error'
        """
        payload_data = {
            "amountDetails": {
                "amount": round(float(amount), 2),
                "currencyCode": currency_code,
            },
            "merchantReference": merchant_reference,
            "reasonForPayment": reason,
            "resultUrl": result_url,
            "returnUrl": return_url,
            "customer": {
                "name": customer_name or "Guest Customer",
                "phone": customer_phone or "",
                "email": customer_email or "",
            },
        }

        try:
            encrypted_payload = self.encrypt_payload(payload_data)
            url = f"{self.base_url}{PESEPAY_MAKE_PAYMENT_PATH}"
            headers = {
                "Authorization": self.integration_key,
                "Content-Type": "application/json",
            }
            body = {"payload": encrypted_payload}

            _logger.info("Initiating Pesepay payment for ref %s (amount: %s %s)", merchant_reference, amount, currency_code)
            response = requests.post(url, json=body, headers=headers, timeout=15)

            if response.status_code in (200, 201):
                resp_json = response.json()
                if "payload" in resp_json:
                    decrypted_response = self.decrypt_payload(resp_json["payload"])
                else:
                    decrypted_response = resp_json

                redirect_url = (
                    decrypted_response.get("redirectUrl")
                    or decrypted_response.get("paymentUrl")
                    or f"{self.base_url}/checkout/{merchant_reference}"
                )
                poll_url = decrypted_response.get("pollUrl", "")
                ref_num = decrypted_response.get("referenceNumber", f"PSP-{merchant_reference}")

                return {
                    "success": True,
                    "redirect_url": redirect_url,
                    "poll_url": poll_url,
                    "reference_number": ref_num,
                    "raw_response": decrypted_response,
                    "error": None,
                }
            else:
                # In sandbox or when mock credentials are used, provide realistic sandbox fallback
                _logger.warning("Pesepay API returned %s: %s", response.status_code, response.text)
                return {
                    "success": False,
                    "redirect_url": None,
                    "poll_url": None,
                    "reference_number": None,
                    "raw_response": response.text,
                    "error": f"Pesepay API Error ({response.status_code}): {response.text}",
                }
        except Exception as exc:
            _logger.error("Exception during Pesepay make-payment: %s", str(exc))
            return {
                "success": False,
                "redirect_url": None,
                "poll_url": None,
                "reference_number": None,
                "raw_response": None,
                "error": str(exc),
            }

    def check_payment_status(self, reference_number):
        """Queries Pesepay for the current status of a payment.

        :param reference_number: Pesepay reference number or merchant reference
        :return: dict with keys: 'success', 'status', 'paid', 'raw_response', 'error'
        """
        try:
            url = f"{self.base_url}{PESEPAY_CHECK_PAYMENT_PATH}"
            headers = {
                "Authorization": self.integration_key,
                "Content-Type": "application/json",
            }
            params = {"referenceNumber": reference_number}
            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                resp_json = response.json()
                if "payload" in resp_json:
                    data = self.decrypt_payload(resp_json["payload"])
                else:
                    data = resp_json

                transaction_status = data.get("transactionStatus", "").upper()
                is_paid = transaction_status in ("SUCCESS", "PAID", "COMPLETED")

                return {
                    "success": True,
                    "status": transaction_status or "UNKNOWN",
                    "paid": is_paid,
                    "raw_response": data,
                    "error": None,
                }
            else:
                return {
                    "success": False,
                    "status": "ERROR",
                    "paid": False,
                    "raw_response": response.text,
                    "error": f"API returned {response.status_code}: {response.text}",
                }
        except Exception as exc:
            return {
                "success": False,
                "status": "ERROR",
                "paid": False,
                "raw_response": None,
                "error": str(exc),
            }
