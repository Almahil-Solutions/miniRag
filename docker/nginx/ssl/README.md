# Nginx TLS Certificates

Place your TLS certificate and private key files in this directory:

- `cert.pem` — Public certificate (or full chain)
- `key.pem` — Private key

## Generating Self-Signed Certificates for Local Development

To generate self-signed certificates for local testing, run:

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout docker/nginx/ssl/key.pem \
  -out docker/nginx/ssl/cert.pem \
  -subj "/CN=localhost"
```

In production, replace these with valid certificates from Let's Encrypt (Certbot) or your certificate authority.
