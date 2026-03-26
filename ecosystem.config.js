/**
 * PM2 Ecosystem Config — ReguTrack
 *
 * NOTE: The FastAPI backend (port 8000) is managed by Docker (docker-compose).
 * PM2 only manages the Next.js frontend.
 *
 * Docs: https://pm2.keymetrics.io/docs/usage/application-declaration/
 */

const path = require("path");
const root = __dirname;

module.exports = {
  apps: [
    // ─── Next.js Frontend ───────────────────────────────────────────
    // Backend API is handled by Docker (see docker-compose.yml, port 8000)
    {
      name: "regutrack-frontend",
      script: "node_modules/next/dist/bin/next",
      args: "start --port 3000",
      cwd: path.join(root, "frontend"),
      interpreter: "node",
      watch: false,
      autorestart: true,
      max_restarts: 20,
      min_uptime: "10s",
      restart_delay: 3000,
      env: {
        NODE_ENV: "production",
        PORT: "3000",
      },
      error_file: path.join(root, "logs", "frontend-error.log"),
      out_file: path.join(root, "logs", "frontend-out.log"),
      log_date_format: "YYYY-MM-DD HH:mm:ss",
      merge_logs: true,
    },
  ],
};
