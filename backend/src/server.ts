import app from "./app.js";
import { initDb } from "./db.js";

const port = Number(process.env.PORT || process.env.BACKEND_PORT || 4000);

initDb()
  .then(() =>
    app.listen(port, "0.0.0.0", () =>
      console.log(`Express listening on ${port}`),
    ),
  )
  .catch((error) => {
    console.error(
      "Backend startup failed while checking database schema:",
      error,
    );
    process.exit(1);
  });
