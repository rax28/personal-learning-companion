# Email/password authentication

The app uses local email/password authentication for application login. Google OAuth is no longer used for sign-in; Google OAuth remains optional and is used only when a signed-in user explicitly connects Google Classroom.

## What it does

- `POST /auth/register`: create an account and a learner profile.
- `POST /auth/login`: verify email/password and issue an HttpOnly session cookie.
- `GET /auth/me`: report whether a valid session exists.
- `POST /auth/logout`: clear the session cookie.
- Passwords are stored as salted scrypt hashes, never plaintext.
- User-owned API requests continue to get `user_id` from the verified session, not from request-body input.

## Run locally

1. Copy `.env.example` to `.env`.
2. Set `JWT_SECRET` to a random secret of at least 32 characters. For example, run `openssl rand -hex 32` and paste the output into `.env`.
3. Start services with `docker compose up --build`.
4. Open `http://localhost:5173`, select **Create one**, and register with an email and password of at least 8 characters.

Google Classroom is configured separately. To use it, set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` and register `http://localhost:4000/oauth/google/classroom/callback` as the authorized redirect URI in Google Cloud. Login does not require Google credentials.

## Existing database volumes

The backend applies the small auth schema migration on startup (`google_sub` becomes nullable and `password_hash` is added). The same migration is also provided at `database/migrations/001_password_auth.sql`.

Accounts created with Google sign-in before this change have no password hash. They cannot sign in with a password until an account migration/password-reset process is provided. Do not allow users to claim an existing email account in production without verifying ownership of that email.

## Production hardening still recommended

Before public deployment, add email verification, password reset, rate limiting/abuse protection, and `COOKIE_SECURE=true` behind HTTPS. Use a unique high-entropy `JWT_SECRET`; do not deploy with the development fallback in `docker-compose.yml`.
