# Security Notes

## What This Repository Intentionally Avoids

This repository is prepared for publication without including:

- WorldQuant account emails
- passwords
- session cookies
- local `.env` files
- local run outputs
- local submission logs

## Recommended Credential Handling

Prefer one of these two approaches:

1. Environment variables
2. A local `.env` file that is ignored by git

Supported variables:

- `WQB_EMAIL`
- `WQB_PASSWORD`
- `WQB_COOKIE_HEADER`
- `WQB_API_BASE`
- `WQB_TIMEOUT`
- `WQB_MAX_WAIT`
- `WQB_POLL_INTERVAL`

## Cookie Handling

If you use `WQB_COOKIE_HEADER`, treat it like a password:

- do not commit it
- do not paste it into tracked files
- rotate it by logging out if you suspect exposure

## Publishing Checklist

Before pushing to a remote repository:

1. Search the workspace for account emails, passwords, and cookie fragments.
2. Make sure `.env`, `.alpha_pipeline/`, `.alpha_pipeline_v2/`, and `__pycache__/` are ignored.
3. Do not commit raw local research outputs unless they have been reviewed and sanitized.
4. Do not commit browser-exported cookies or screenshots containing account details.

## Operational Advice

- Use a dedicated local environment for research runs.
- Prefer a lower-privilege account if one is available.
- Expect reCAPTCHA or account-specific restrictions to interrupt fully automated login.
- Review submission blockers before auto-submit is enabled.
