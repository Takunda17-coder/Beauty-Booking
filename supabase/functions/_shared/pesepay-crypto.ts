// Deno AES-256-CBC Crypto helper for Pesepay Gateway
import { encode as base64Encode, decode as base64Decode } from "https://deno.land/std@0.208.0/encoding/base64.ts";

export class PesepayCrypto {
  private keyBytes: Uint8Array;
  private ivBytes: Uint8Array;

  constructor(encryptionKey: string) {
    if (!encryptionKey || encryptionKey.length !== 32) {
      throw new Error("Pesepay encryption key must be exactly 32 characters long.");
    }
    const encoder = new TextEncoder();
    this.keyBytes = encoder.encode(encryptionKey);
    this.ivBytes = encoder.encode(encryptionKey.substring(0, 16));
  }

  async encrypt(payloadData: Record<string, unknown>): Promise<string> {
    const jsonStr = JSON.stringify(payloadData);
    const rawBytes = new TextEncoder().encode(jsonStr);

    // PKCS7 padding to 16-byte blocks
    const blockSize = 16;
    const paddingLength = blockSize - (rawBytes.length % blockSize);
    const paddedBytes = new Uint8Array(rawBytes.length + paddingLength);
    paddedBytes.set(rawBytes);
    paddedBytes.fill(paddingLength, rawBytes.length);

    const key = await crypto.subtle.importKey(
      "raw",
      this.keyBytes,
      { name: "AES-CBC" },
      false,
      ["encrypt"]
    );

    const encrypted = await crypto.subtle.encrypt(
      { name: "AES-CBC", iv: this.ivBytes },
      key,
      paddedBytes
    );

    return base64Encode(encrypted);
  }

  async decrypt(base64Payload: string): Promise<Record<string, unknown>> {
    const cipherBytes = base64Decode(base64Payload);

    const key = await crypto.subtle.importKey(
      "raw",
      this.keyBytes,
      { name: "AES-CBC" },
      false,
      ["decrypt"]
    );

    const decryptedPadded = await crypto.subtle.decrypt(
      { name: "AES-CBC", iv: this.ivBytes },
      key,
      cipherBytes
    );

    const decryptedBytes = new Uint8Array(decryptedPadded);
    const paddingLength = decryptedBytes[decryptedBytes.length - 1];
    const unpadded = decryptedBytes.subarray(0, decryptedBytes.length - paddingLength);

    const jsonStr = new TextDecoder().decode(unpadded);
    return JSON.parse(jsonStr);
  }
}
