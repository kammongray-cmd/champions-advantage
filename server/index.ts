import express from "express";
import cors from "cors";
import path from "path";
import http from "http";
import { WebSocketServer } from "ws";
import { router } from "./routes";

const app = express();
const PORT = 5000;

app.use(cors());
app.use(express.json({ limit: "10mb" }));

app.use("/api", router);

app.get("/_stcore/health", (_req, res) => {
  res.status(200).send("ok");
});

const uploadsDir = path.resolve(process.cwd(), "uploads");
app.use("/uploads", express.static(uploadsDir));

const clientDist = path.resolve(__dirname, "../dist/public");
app.use(express.static(clientDist));

app.get("/{*splat}", (_req, res) => {
  res.sendFile(path.join(clientDist, "index.html"));
});

const server = http.createServer(app);

const wss = new WebSocketServer({ server, path: "/_stcore/stream" });
wss.on("connection", (ws) => {
  ws.send(JSON.stringify({
    type: "sessionStatusChanged",
    sessionStatus: { runOnSave: false, scriptIsRunning: false },
  }));
  setTimeout(() => ws.close(), 100);
});

server.listen(PORT, "0.0.0.0", () => {
  console.log(`Server running on port ${PORT}`);
});
