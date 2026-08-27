import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const SRC_DIR = dirname(fileURLToPath(import.meta.url));

const APP_REGISTRY = "/app/registry/registry.json";
const REPO_REGISTRY = resolve(SRC_DIR, "../../registry/registry.json");

export function defaultRegistryPath(): string {
  if (process.env.REGISTRY_PATH) return process.env.REGISTRY_PATH;
  if (existsSync(APP_REGISTRY)) return APP_REGISTRY;
  return REPO_REGISTRY;
}
