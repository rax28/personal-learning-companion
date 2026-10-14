import express from "express";
import cors from "cors";
import { z } from "zod";
import { randomUUID } from "node:crypto";
import cookieParser from "cookie-parser";
import { q } from "./db.js";
import {
  requireAuth,
  register,
  login,
  logout,
  me,
  AuthRequest,
} from "./auth.js";
import { OAuth2Client } from "google-auth-library";

const app = express();

app.use(
  cors({
    origin: process.env.FRONTEND_URL || "http://localhost:5173",
    credentials: true,
  }),
);
app.use(express.json({ limit: "40mb" }));
app.use(cookieParser());

const aiBase = () => process.env.AI_BACKEND_URL || "http://localhost:8000";
const aiRequest = (req: AuthRequest, path: string, init: RequestInit = {}) =>
  fetch(aiBase() + path, {
    ...init,
    headers: {
      ...(init.headers || {}),
      "x-user-id": req.user!.id,
      "x-internal-token": process.env.AI_INTERNAL_TOKEN || "change-me",
    },
  });

app.get("/health", (_, res) => res.json({ ok: true, service: "backend" }));
app.post("/auth/register", register);
app.post("/auth/login", login);
app.post("/auth/logout", logout);
app.get("/auth/me", me);

app.use((req, res, next) => {
  if (req.path === "/oauth/google/classroom/callback") {
    return next();
  }

  return requireAuth(req as AuthRequest, res, next);
});

app.post("/goals", async (req: AuthRequest, res) => {
  const p = z
    .object({
      title: z.string().min(1),
      mode: z
        .enum(["education", "self", "interview", "professional", "personal"])
        .default("personal"),
    })
    .parse(req.body);
  const r = await q<any>(
    'INSERT INTO goals(user_id,title,mode) VALUES($1,$2,$3) RETURNING id,title,mode,created_at AS "createdAt"',
    [req.user!.id, p.title, p.mode],
  );
  const g = r.rows[0];
  await q(
    "INSERT INTO conversations(id,user_id,mode) VALUES($1,$2,$3) ON CONFLICT DO NOTHING",
    [g.id, req.user!.id, p.mode],
  );
  res.status(201).json(g);
});

app.get("/goals", async (req: AuthRequest, res) => {
  const r = await q<any>(
    'SELECT id,title,mode,created_at AS "createdAt" FROM goals WHERE user_id=$1 ORDER BY created_at DESC',
    [req.user!.id],
  );
  res.json(r.rows);
});

app.get("/user/learner-state", async (req: AuthRequest, res) => {
  try {
    const r = await aiRequest(req, "/learning/state");
    res
      .status(r.status)
      .type("application/json")
      .send(await r.text());
  } catch (e) {
    res
      .status(502)
      .json({ error: "Learning state service unavailable", detail: String(e) });
  }
});

app.get("/learning/state", async (req: AuthRequest, res) => {
  try {
    const r = await aiRequest(req, "/learning/state");
    res
      .status(r.status)
      .type("application/json")
      .send(await r.text());
  } catch (e) {
    res
      .status(502)
      .json({ error: "Learning state service unavailable", detail: String(e) });
  }
});

app.get("/learning/profile", async (req: AuthRequest, res) => {
  try {
    const r = await aiRequest(req, "/learning/profile");
    res
      .status(r.status)
      .type("application/json")
      .send(await r.text());
  } catch (e) {
    res.status(502).json({
      error: "Learning profile service unavailable",
      detail: String(e),
    });
  }
});
app.put("/learning/profile", async (req: AuthRequest, res) => {
  try {
    const r = await aiRequest(req, "/learning/profile", {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(req.body),
    });
    res
      .status(r.status)
      .type("application/json")
      .send(await r.text());
  } catch (e) {
    res.status(502).json({
      error: "Learning profile service unavailable",
      detail: String(e),
    });
  }
});
for (const route of [
  "concepts",
  "history",
  "assessment-evidence",
  "mastery-updates",
  "relationships",
]) {
  app.get(`/learning/${route}`, async (req: AuthRequest, res) => {
    try {
      const query = new URLSearchParams(
        req.query as Record<string, string>,
      ).toString();
      const r = await aiRequest(
        req,
        `/learning/${route}${query ? `?${query}` : ""}`,
      );
      res
        .status(r.status)
        .type("application/json")
        .send(await r.text());
    } catch (e) {
      res
        .status(502)
        .json({ error: "Learning service unavailable", detail: String(e) });
    }
  });
}

app.get("/conversation/:id", async (req: AuthRequest, res) => {
  const r = await q<any>(
    'SELECT id,role,content,created_at AS "createdAt",topic FROM messages WHERE user_id=$1 AND conversation_id=$2 ORDER BY created_at',
    [req.user!.id, req.params.id],
  );
  res.json(r.rows);
});

app.post("/conversation/message", async (req: AuthRequest, res) => {
  try {
    const p = z
      .object({
        message: z.string().min(1),
        goalId: z.string().optional(),
        conversationId: z.string().optional(),
        mode: z
          .enum(["education", "self", "interview", "professional", "personal"])
          .default("education"),
        topicHint: z.string().optional(),
        sourceId: z.string().optional(),
        sourceIds: z.array(z.string()).optional(),
      })
      .parse(req.body);
    let conversationId = p.conversationId || p.goalId || "default";
    const existing = p.topicHint
      ? await q<any>(
          "SELECT id FROM conversations WHERE user_id=$1 AND mode=$2 AND lower(topic)=lower($3) ORDER BY updated_at DESC LIMIT 1",
          [req.user!.id, p.mode, p.topicHint],
        )
      : { rows: [] };
    if (existing.rows[0]) conversationId = existing.rows[0].id;
    await q(
      "INSERT INTO conversations(id,user_id,mode,topic) VALUES($1,$2,$3,$4) ON CONFLICT(user_id,id) DO UPDATE SET topic=COALESCE($4,conversations.topic),updated_at=now()",
      [conversationId, req.user!.id, p.mode, p.topicHint || null],
    );
    const h = await q<any>(
      'SELECT id,role,content,created_at AS "createdAt",topic FROM messages WHERE user_id=$1 AND conversation_id=$2 ORDER BY created_at DESC LIMIT 12',
      [req.user!.id, conversationId],
    );
    const r = await aiRequest(req, "/internal/chat", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        message: p.message,
        conversationId,
        mode: p.mode,
        topicHint: p.topicHint,
        history: h.rows.reverse(),
        goal: undefined,
        learnerContext: {},
        sourceId: p.sourceId,
        sourceIds: p.sourceIds || [],
      }),
    });
    if (!r.ok) throw new Error(`AI backend ${r.status}: ${await r.text()}`);
    const d: any = await r.json();
    const resolved = d.conversationId || conversationId;
    if (resolved !== conversationId)
      await q(
        "INSERT INTO conversations(id,user_id,mode,topic) VALUES($1,$2,$3,$4) ON CONFLICT DO NOTHING",
        [resolved, req.user!.id, p.mode, d.topic || p.topicHint || null],
      );
    await q(
      "INSERT INTO messages(user_id,conversation_id,role,content,topic) VALUES($1,$2,$3,$4,$5),($1,$2,$6,$7,$5)",
      [
        req.user!.id,
        resolved,
        "user",
        p.message,
        d.topic || p.topicHint || null,
        "assistant",
        d.response,
      ],
    );
    await q(
      "UPDATE conversations SET topic=$3,updated_at=now() WHERE user_id=$1 AND id=$2",
      [req.user!.id, resolved, d.topic || p.topicHint || null],
    );
    res.json({
      response: d.response,
      learnerState: d.learnerState,
      evidence: d.evidence,
      topic: d.topic,
      conversationId: resolved,
      topicThreadId: resolved,
    });
  } catch (e) {
    console.error("Conversation error:", e);
    res
      .status(502)
      .json({ error: "Companion request failed", detail: String(e) });
  }
});

/**
 * Source Lab proxy routes.
 * The browser talks only to the Node gateway (port 4000), so these routes
 * prevent cross-origin/CORS failures when the AI service is on port 8000.
 */
app.get("/compression/source-default", async (req: AuthRequest, res) => {
  try {
    const r = await aiRequest(req, "/compression/source-default");
    const text = await r.text();
    res.status(r.status).type("application/json").send(text);
  } catch (e) {
    res
      .status(502)
      .json({ error: "Compression service unavailable", detail: String(e) });
  }
});

app.options("/compression/load-source", cors());
app.post("/compression/load-source", async (req: AuthRequest, res) => {
  try {
    const r = await aiRequest(req, "/compression/load-source", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(req.body),
    });
    const text = await r.text();
    res.status(r.status).type("application/json").send(text);
  } catch (e) {
    res.status(502).json({
      error: "Compression source load unavailable",
      detail: String(e),
    });
  }
});

app.options("/compression/compress", cors());
app.post("/compression/compress", async (req: AuthRequest, res) => {
  try {
    const r = await aiRequest(req, "/compression/compress", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(req.body),
    });
    const text = await r.text();
    res.status(r.status).type("application/json").send(text);
  } catch (e) {
    res
      .status(502)
      .json({ error: "Compression service unavailable", detail: String(e) });
  }
});

app.options("/compression/decompress", cors());
app.post("/compression/decompress", async (req: AuthRequest, res) => {
  try {
    const r = await aiRequest(req, "/compression/decompress", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(req.body),
    });
    const text = await r.text();
    res.status(r.status).type("application/json").send(text);
  } catch (e) {
    res
      .status(502)
      .json({ error: "Compression service unavailable", detail: String(e) });
  }
});

app.options("/source/cache", cors());
app.post("/source/cache", async (req: AuthRequest, res) => {
  try {
    const r = await aiRequest(req, "/source/cache", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(req.body),
    });
    const text = await r.text();
    res.status(r.status).type("application/json").send(text);
  } catch (e) {
    res
      .status(502)
      .json({ error: "Source cache unavailable", detail: String(e) });
  }
});

app.get("/source/cache", async (req: AuthRequest, res) => {
  try {
    const r = await aiRequest(req, "/source/cache");
    const text = await r.text();
    res.status(r.status).type("application/json").send(text);
  } catch (e) {
    res
      .status(502)
      .json({ error: "Source cache unavailable", detail: String(e) });
  }
});

app.post("/source/upload", async (req: AuthRequest, res) => {
  try {
    const r = await aiRequest(req, "/source/upload", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(req.body),
    });
    const text = await r.text();
    res.status(r.status).type("application/json").send(text);
  } catch (e) {
    res
      .status(502)
      .json({ error: "Source upload unavailable", detail: String(e) });
  }
});

app.get("/source/cache/:id", async (req, res) => {
  try {
    const r = await aiRequest(
      req,
      "/source/cache/" + encodeURIComponent(req.params.id),
    );
    const text = await r.text();
    res.status(r.status).type("application/json").send(text);
  } catch (e) {
    res
      .status(502)
      .json({ error: "Source cache unavailable", detail: String(e) });
  }
});

app.post("/source/cache/:id/search", async (req, res) => {
  try {
    const r = await aiRequest(
      req,
      "/source/cache/" + encodeURIComponent(req.params.id) + "/search",
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(req.body),
      },
    );
    const text = await r.text();
    res.status(r.status).type("application/json").send(text);
  } catch (e) {
    res
      .status(502)
      .json({ error: "Source retrieval unavailable", detail: String(e) });
  }
});

app.get("/learning/graph", async (req: AuthRequest, res) => {
  try {
    const r = await aiRequest(req, "/graph");
    const text = await r.text();
    res.status(r.status).type("application/json").send(text);
  } catch (e) {
    res
      .status(502)
      .json({ error: "Knowledge graph unavailable", detail: String(e) });
  }
});

app.get("/learning/graph/:mode", async (req: AuthRequest, res) => {
  try {
    const r = await aiRequest(
      req,
      "/graph/" + encodeURIComponent(String(req.params.mode)),
    );
    const text = await r.text();
    res.status(r.status).type("application/json").send(text);
  } catch (e) {
    res
      .status(502)
      .json({ error: "Knowledge graph unavailable", detail: String(e) });
  }
});

app.get("/learning/gaps", async (req: AuthRequest, res) => {
  try {
    const r = await aiRequest(req, "/gaps");
    const text = await r.text();
    res.status(r.status).type("application/json").send(text);
  } catch (e) {
    res
      .status(502)
      .json({ error: "Learning gaps unavailable", detail: String(e) });
  }
});

app.get("/learning/misconceptions", async (req: AuthRequest, res) => {
  const r = await aiRequest(req, "/learning/state");
  const d: any = await r.json();
  res.json(d.misconceptions || []);
});
app.get("/learning/progress", async (req: AuthRequest, res) => {
  const r = await aiRequest(req, "/learning/state");
  const d: any = await r.json();
  res.json(d.learningHistory || []);
});
app.get("/sync/state", async (req: AuthRequest, res) => {
  const r = await aiRequest(req, "/learning/state");
  res
    .status(r.status)
    .type("application/json")
    .send(await r.text());
});
app.post("/sync/state", async (req: AuthRequest, res) => {
  // Sync is now a user-scoped operation; the durable learner graph remains authoritative.
  const r = await aiRequest(req, "/learning/state");
  res
    .status(r.status)
    .type("application/json")
    .send(await r.text());
});

// Google Classroom uses a second, user-scoped OAuth grant. Login identity and Classroom
// authorization are separate, while both are attached to the same Postgres user.
const classroomScopes = [
  "https://www.googleapis.com/auth/classroom.courses.readonly",
  "https://www.googleapis.com/auth/classroom.coursework.me.readonly",
  "https://www.googleapis.com/auth/classroom.coursework.students.readonly",
  "https://www.googleapis.com/auth/classroom.announcements.readonly",
  "https://www.googleapis.com/auth/classroom.courseworkmaterials.readonly",
  "https://www.googleapis.com/auth/drive.readonly",
];
const classroomRedirect = () =>
  process.env.GOOGLE_CLASSROOM_REDIRECT_URI ||
  "http://localhost:4000/oauth/google/classroom/callback";
const classroomStateCookieAttributes = () =>
  process.env.COOKIE_SECURE === "true"
    ? "SameSite=None; Secure"
    : "SameSite=Lax";
const googleConfigured = () =>
  Boolean(process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET);

async function userGoogleToken(userId: string) {
  const r = await q<any>(
    "SELECT * FROM oauth_tokens WHERE user_id=$1 AND provider=$2",
    [userId, "google-classroom"],
  );
  if (!r.rows[0]) throw new Error("Google Classroom is not connected");
  const t = r.rows[0];
  if (
    t.expires_at &&
    new Date(t.expires_at).getTime() > Date.now() + 60000 &&
    t.access_token
  )
    return t.access_token;
  if (!t.refresh_token)
    throw new Error(
      "Google Classroom authorization expired; reconnect Classroom",
    );
  const client = new (await import("google-auth-library")).OAuth2Client(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET,
    classroomRedirect(),
  );
  client.setCredentials({ refresh_token: t.refresh_token });
  const { credentials } = await client.refreshAccessToken();
  await q(
    `UPDATE oauth_tokens SET access_token=$2,expires_at=$3,scope=COALESCE($4,scope),updated_at=now() WHERE user_id=$1 AND provider='google-classroom'`,
    [
      userId,
      credentials.access_token,
      credentials.expiry_date ? new Date(credentials.expiry_date) : null,
      credentials.scope || null,
    ],
  );
  return credentials.access_token;
}
async function googleApiForUser(
  userId: string,
  pathname: string,
  init: RequestInit = {},
) {
  const token = await userGoogleToken(userId);
  return fetch("https://classroom.googleapis.com" + pathname, {
    ...init,
    headers: { ...(init.headers || {}), Authorization: "Bearer " + token },
  });
}
async function driveApiForUser(
  userId: string,
  pathname: string,
  init: RequestInit = {},
) {
  const token = await userGoogleToken(userId);
  return fetch("https://www.googleapis.com/drive/v3" + pathname, {
    ...init,
    headers: { ...(init.headers || {}), Authorization: "Bearer " + token },
  });
}

app.get("/integrations/google/classroom/start", (req: AuthRequest, res) => {
  if (!googleConfigured()) {
    return res
      .status(503)
      .json({ error: "Google authentication is not configured" });
  }

  const state = Buffer.from(
    JSON.stringify({ userId: req.user!.id, nonce: randomUUID() }),
  ).toString("base64url");

  res.setHeader(
    "Set-Cookie",
    `plc_classroom_state=${state}; HttpOnly; ${classroomStateCookieAttributes()}; Path=/; Max-Age=600`,
  );

  const client = new OAuth2Client(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET,
    classroomRedirect(),
  );

  const url = client.generateAuthUrl({
    access_type: "offline",
    prompt: "consent",
    scope: classroomScopes,
    state,
  });

  res.json({ url });
});

app.get("/oauth/google/classroom/callback", async (req, res) => {
  try {
    const cookie = (req.headers.cookie || "")
      .split(";")
      .map((x) => x.trim())
      .find((x) => x.startsWith("plc_classroom_state="))
      ?.split("=")[1];
    const state = JSON.parse(
      Buffer.from(String(req.query.state || ""), "base64url").toString(),
    );
    // if (!cookie || cookie !== String(req.query.state || "") || !state.userId)
    //   return res.status(400).send("Invalid Classroom OAuth state");
    console.log("Classroom OAuth state check:", {
      cookiePresent: Boolean(cookie),
      statePresent: Boolean(req.query.state),
      cookieMatches: Boolean(
        cookie && cookie === String(req.query.state || ""),
      ),
      userIdPresent: Boolean(state?.userId),
    });
    const client = new OAuth2Client(
      process.env.GOOGLE_CLIENT_ID,
      process.env.GOOGLE_CLIENT_SECRET,
      classroomRedirect(),
    );
    const { tokens } = await client.getToken(String(req.query.code || ""));
    await q(
      `INSERT INTO oauth_tokens(user_id,provider,access_token,refresh_token,expires_at,scope) VALUES($1,'google-classroom',$2,$3,$4,$5)
      ON CONFLICT(user_id) DO UPDATE SET access_token=COALESCE(EXCLUDED.access_token,oauth_tokens.access_token),refresh_token=COALESCE(EXCLUDED.refresh_token,oauth_tokens.refresh_token),expires_at=EXCLUDED.expires_at,scope=EXCLUDED.scope,updated_at=now()`,
      [
        state.userId,
        tokens.access_token || null,
        tokens.refresh_token || null,
        tokens.expiry_date ? new Date(tokens.expiry_date) : null,
        tokens.scope || null,
      ],
    );
    res.setHeader(
      "Set-Cookie",
      `plc_classroom_state=; HttpOnly; ${classroomStateCookieAttributes()}; Path=/; Max-Age=0`,
    );
    res.redirect(
      (process.env.FRONTEND_URL || "http://localhost:5173") +
        "/?classroom=connected",
    );
  } catch (e) {
    console.error(e);
    res.status(500).send("Google Classroom connection failed");
  }
});

app.get(
  "/integrations/google/classroom/status",
  async (req: AuthRequest, res) => {
    const r = await q<any>(
      "SELECT access_token,refresh_token FROM oauth_tokens WHERE user_id=$1 AND provider='google-classroom'",
      [req.user!.id],
    );
    res.json({
      connected: Boolean(r.rows[0]?.access_token || r.rows[0]?.refresh_token),
      configured: googleConfigured(),
    });
  },
);
app.get(
  "/integrations/google/classroom/courses",
  async (req: AuthRequest, res) => {
    try {
      const r = await googleApiForUser(
        req.user!.id,
        "/v1/courses?pageSize=100",
      );
      res
        .status(r.status)
        .type("application/json")
        .send(await r.text());
    } catch (e) {
      res.status(401).json({ error: String(e) });
    }
  },
);
app.get(
  "/integrations/google/classroom/courses/:courseId/materials",
  async (req: AuthRequest, res) => {
    try {
      const [m, w] = await Promise.all([
        googleApiForUser(
          req.user!.id,
          "/v1/courses/" +
            encodeURIComponent(String(req.params.courseId)) +
            "/courseWorkMaterials?pageSize=100",
        ),
        googleApiForUser(
          req.user!.id,
          "/v1/courses/" +
            encodeURIComponent(String(req.params.courseId)) +
            "/courseWork?pageSize=100",
        ),
      ]);
      const materials = m.ok
        ? ((await m.json()) as any)
        : { courseWorkMaterial: [] };
      const work = w.ok ? ((await w.json()) as any) : { courseWork: [] };
      const items: any[] = [];
      for (const x of [
        ...(materials.courseWorkMaterial || []),
        ...(work.courseWork || []),
      ])
        for (const a of x.materials || [])
          if (a.driveFile?.driveFile?.id)
            items.push({
              id: a.driveFile.driveFile.id,
              title: a.driveFile.driveFile.title || x.title || "Classroom file",
              mimeType: a.driveFile.driveFile.mimeType,
              courseId: req.params.courseId,
              workId: x.id,
              url: a.driveFile.driveFile.alternateLink,
            });
      res.json({ materials: items });
    } catch (e) {
      res.status(401).json({ error: String(e) });
    }
  },
);
app.post(
  "/integrations/google/classroom/import",
  async (req: AuthRequest, res) => {
    try {
      const fileId = String(req.body?.fileId || "");
      if (!fileId) return res.status(400).json({ error: "fileId is required" });
      const metaR = await driveApiForUser(
        req.user!.id,
        "/files/" +
          encodeURIComponent(fileId) +
          "?fields=id,name,mimeType,webViewLink,size",
      );
      if (!metaR.ok) return res.status(metaR.status).send(await metaR.text());
      const meta = (await metaR.json()) as any;
      const dataR = await driveApiForUser(
        req.user!.id,
        "/files/" + encodeURIComponent(fileId) + "?alt=media",
      );
      if (!dataR.ok) return res.status(dataR.status).send(await dataR.text());
      const bytes = Buffer.from(await dataR.arrayBuffer()).toString("base64");
      const ai = await aiRequest(req, "/source/upload", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          filename: meta.name,
          contentBase64: bytes,
          mimeType: meta.mimeType,
          sourceUrl: "google-classroom://" + fileId,
        }),
      });
      res
        .status(ai.status)
        .type("application/json")
        .send(await ai.text());
    } catch (e) {
      res
        .status(502)
        .json({ error: "Classroom import failed", detail: String(e) });
    }
  },
);
export default app;
