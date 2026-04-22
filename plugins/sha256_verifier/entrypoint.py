#!/usr/bin/env python3
"""SHA-256 webhook signature verifier plugin entrypoint."""
import argparse
import hashlib
import hmac
import sys


def verify(secret: str, payload: bytes, provided_signature: str) -> bool:
    expected = 'sha256=' + hmac.new(secret.encode('utf-8'), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, provided_signature.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description='Verify webhook signature (HMAC SHA-256).')
    parser.add_argument('--secret', required=True)
    parser.add_argument('--signature', required=True, help='Expected format: sha256=<hex>')
    parser.add_argument('--payload-file', required=True)
    args = parser.parse_args()

    with open(args.payload_file, 'rb') as f:
        payload = f.read()

    ok = verify(args.secret, payload, args.signature)
    print('VERIFIED' if ok else 'INVALID')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
