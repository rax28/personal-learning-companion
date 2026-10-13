import { Request, Response, NextFunction } from "express";
import { OAuth2Client } from "google-auth-library";
import jwt from "jsonwebtoken";
import {
  randomBytes,
  scrypt as scryptCallback,
  timingSafeEqual,
} from "node:crypto";
import { promisify } from "node:util";
import { q } from "./db.js";

const scrypt = promisify(scryptCallback);
const google = () =>
  new OAuth2Client(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET,
    process.env.GOOGLE_CLASSROOM_REDIRECT_URI ||
      "http://localhost:4000/oauth/google/classroom/callback",
  );
const secret = () => {
  const value = process.env.JWT_SECRET;
  if (!value || value.length < 32)
    throw new Error(
      "JWT_SECRET must be set to a random value of at least 32 characters",
    );
  return value;
};
const frontend = () => process.env.FRONTEND_URL || "http://localhost:5173";
const cookieSecure = () => "; Secure";

const sessionCookie = (token: string) =>
  `plc_session=${token}; HttpOnly; SameSite=None; Secure; Path=/; Max-Age=604800`;

const clearCookie = () =>
  `plc_session=; HttpOnly; SameSite=None; Secure; Path=/; Max-Age=0`;
export type AuthRequest = Request & {
  user?: { id: string; email: string; name: string; picture?: string };
};

function readSession(req: Request) {
  const token =
    (req as any).cookies?.plc_session ||
    String(req.headers.authorization || "").replace(/^Bearer\s+/, "");
  if (!token) return null;
  try {
    const payload: any = jwt.verify(token, secret());
    if (!payload.sub || !payload.email) return null;
    return {
      id: String(payload.sub),
      email: String(payload.email),
      name: String(payload.name || payload.email),
      picture: payload.picture as string | undefined,
    };
  } catch {
    return null;
  }
}

export function requireAuth(
  req: AuthRequest,
  res: Response,
  next: NextFunction,
) {
  const user = readSession(req);
  if (!user) return res.status(401).json({ error: "Authentication required" });
  req.user = user;
  next();
}

async function passwordHash(password: string) {
  const salt = randomBytes(16).toString("hex");
  const key = (await scrypt(password, salt, 64)) as Buffer;
  return `scrypt:${salt}:${key.toString("hex")}`;
}
async function passwordMatches(password: string, encoded: string) {
  const [scheme, salt, hash] = encoded.split(":");
  if (scheme !== "scrypt" || !salt || !hash) return false;
  const expected = Buffer.from(hash, "hex");
  const actual = (await scrypt(password, salt, expected.length)) as Buffer;
  return expected.length === actual.length && timingSafeEqual(expected, actual);
}
function createSession(user: {
  id: string;
  email: string;
  display_name: string;
  avatar_url?: string | null;
}) {
  return jwt.sign(
    {
      sub: user.id,
      email: user.email,
      name: user.display_name,
      picture: user.avatar_url || undefined,
    },
    secret(),
    { expiresIn: "7d" },
  );
}

export async function register(req: Request, res: Response) {
  try {
    const email = String(req.body?.email || "")
      .trim()
      .toLowerCase();
    const password = String(req.body?.password || "");
    const name = String(req.body?.name || "").trim();
    if (!/^\S+@\S+\.\S+$/.test(email))
      return res.status(400).json({ error: "Enter a valid email address." });
    if (password.length < 8)
      return res
        .status(400)
        .json({ error: "Password must be at least 8 characters." });
    if (password.length > 200)
      return res.status(400).json({ error: "Password is too long." });
    const displayName = name.slice(0, 100) || email.split("@")[0];
    const hashed = await passwordHash(password);
    const inserted = await q<any>(
      `INSERT INTO users(google_sub,email,display_name,password_hash,last_login_at)
      VALUES(NULL,$1,$2,$3,now()) ON CONFLICT(email) DO NOTHING
      RETURNING id,email,display_name,avatar_url`,
      [email, displayName, hashed],
    );
    if (!inserted.rows[0])
      return res
        .status(409)
        .json({
          error: "An account with this email already exists. Sign in instead.",
        });
    const user = inserted.rows[0];
    await q(
      "INSERT INTO learner_profile(user_id,display_name) VALUES($1,$2) ON CONFLICT(user_id) DO NOTHING",
      [user.id, user.display_name],
    );
    res.setHeader("Set-Cookie", sessionCookie(createSession(user)));
    return res
      .status(201)
      .json({
        authenticated: true,
        user: { id: user.id, email: user.email, name: user.display_name },
      });
  } catch (e) {
    console.error("Registration failed:", e);
    return res
      .status(500)
      .json({
        error:
          "Could not create account. Check the server configuration and try again.",
      });
  }
}

export async function login(req: Request, res: Response) {
  try {
    const email = String(req.body?.email || "")
      .trim()
      .toLowerCase();
    const password = String(req.body?.password || "");
    const result = await q<any>(
      "SELECT id,email,display_name,avatar_url,password_hash FROM users WHERE lower(email)=lower($1) LIMIT 1",
      [email],
    );
    const user = result.rows[0];
    if (
      !user?.password_hash ||
      !(await passwordMatches(password, user.password_hash))
    ) {
      return res.status(401).json({ error: "Email or password is incorrect." });
    }
    await q(
      "UPDATE users SET last_login_at=now(),updated_at=now() WHERE id=$1",
      [user.id],
    );
    res.setHeader("Set-Cookie", sessionCookie(createSession(user)));
    return res.json({
      authenticated: true,
      user: { id: user.id, email: user.email, name: user.display_name },
    });
  } catch (e) {
    console.error("Login failed:", e);
    return res
      .status(500)
      .json({
        error:
          "Could not sign in. Check the server configuration and try again.",
      });
  }
}

export function logout(_: Request, res: Response) {
  res.setHeader("Set-Cookie", clearCookie());
  res.json({ ok: true });
}
export function me(req: Request, res: Response) {
  const user = readSession(req);
  if (!user) return res.status(200).json({ authenticated: false });
  return res.json({ authenticated: true, user });
}

// Google remains available only for the optional Google Classroom integration.
export function googleClient() {
  return google();
}
