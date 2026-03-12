# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest (`main`) | ✅ |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it responsibly:

1. **DO NOT** open a public issue
2. Email: [Create a private security advisory](https://github.com/TadFuji/ai-news-bot/security/advisories/new)
3. Include: description of the vulnerability, steps to reproduce, and potential impact

We will acknowledge your report within 48 hours and provide a timeline for a fix.

## Security Best Practices

This project follows these security practices:

- API keys are stored exclusively in environment variables and GitHub Secrets
- `.env` is gitignored and never committed
- No secrets in Git history (verified via audit)
- Dependencies are reviewed for known vulnerabilities
