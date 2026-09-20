#!/bin/bash
# Generates a self-signed SSL certificate for localhost development

# Ensure we are in the correct directory (the script's directory)
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SSL_DIR="${DIR}/ssl"

mkdir -p "${SSL_DIR}"

echo "Generating Self-Signed SSL Certificate for localhost..."

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "${SSL_DIR}/key.pem" \
    -out "${SSL_DIR}/cert.pem" \
    -subj "/C=US/ST=State/L=City/O=EdgeSentinel/CN=localhost"

echo "Certificate generated successfully in ${SSL_DIR}"
echo " - cert.pem"
echo " - key.pem"
