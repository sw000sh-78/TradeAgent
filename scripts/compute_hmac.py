#!/usr/bin/env python3
"""Compute HMAC-SHA256 hex signature for a file.

Usage:
  ./scripts/compute_hmac.py -s SECRET -f path/to/file.json
Or set SECRET env var and run:
  SECRET=foo ./scripts/compute_hmac.py tests/sample_payload.json
"""
import argparse
import hmac
import hashlib
import os
import sys


def compute_hmac(secret: bytes, data: bytes) -> str:
    return hmac.new(secret, data, hashlib.sha256).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", nargs="?", help="file to read; default stdin if omitted")
    parser.add_argument("-s", "--secret", help="secret key (or set SECRET env var)")
    args = parser.parse_args()

    secret = args.secret or os.getenv("SECRET") or os.getenv("WEBHOOK_SECRET")
    if not secret:
        print("ERROR: secret not provided via -s or SECRET/WEBHOOK_SECRET env var", file=sys.stderr)
        sys.exit(2)

    if args.file:
        with open(args.file, "rb") as f:
            data = f.read()
    else:
        data = sys.stdin.buffer.read()

    sig = compute_hmac(secret.encode(), data)
    print(sig)


if __name__ == "__main__":
    main()
