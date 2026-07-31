import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';

const webDirectory = path.dirname(fileURLToPath(import.meta.url));
const webEnvPath = path.resolve(webDirectory, '../.env.web');

function readWebEnvironment() {
  if (!fs.existsSync(webEnvPath)) return {};

  return fs.readFileSync(webEnvPath, 'utf8')
    .split(/\r?\n/)
    .reduce((values, line) => {
      const normalized = line.trim();
      if (!normalized || normalized.startsWith('#')) return values;

      const separator = normalized.indexOf('=');
      if (separator < 1) return values;

      const key = normalized.slice(0, separator).trim();
      const value = normalized.slice(separator + 1).trim().replace(/^['"]|['"]$/g, '');
      values[key] = value;
      return values;
    }, {});
}

const webEnvironment = readWebEnvironment();
const developmentPort = Number(webEnvironment.WEB_DEV_PORT || 5173);
const developmentApiUrl = webEnvironment.WEB_DEV_API_UPSTREAM_URL || 'http://localhost:8000';

export default defineConfig({
  esbuild: {
    jsx: 'automatic',
  },
  optimizeDeps: {
    esbuildOptions: {
      jsx: 'automatic',
    },
  },
  server: {
    port: developmentPort,
    proxy: {
      '/api': {
        target: developmentApiUrl,
        changeOrigin: true,
        rewrite: (requestPath) => requestPath.replace(/^\/api/, ''),
      },
    },
  },
});
