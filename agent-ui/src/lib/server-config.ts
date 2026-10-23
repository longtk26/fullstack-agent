import "server-only";

export const API_URL = (process.env.API_URL ?? "http://localhost:8100").replace(/\/$/, "");
export const AUTH_COOKIE_NAME = "bga_token";
