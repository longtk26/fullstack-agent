"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { API_URL, AUTH_COOKIE_NAME } from "@/lib/server-config";
import type { TLoginResult } from "@/types/auth";

export async function loginAction(email: string, password: string): Promise<TLoginResult> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
      cache: "no-store",
    });
  } catch {
    return { ok: false, message: "The agent API is unreachable" };
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    return { ok: false, message: body?.error?.message ?? "Login failed" };
  }
  const { accessToken, expiresIn } = (await response.json()) as { accessToken: string; expiresIn: number };
  const cookieStore = await cookies();
  cookieStore.set(AUTH_COOKIE_NAME, accessToken, {
    httpOnly: true,
    secure: process.env.COOKIE_SECURE === "true",
    sameSite: "lax",
    path: "/",
    maxAge: expiresIn,
  });
  return { ok: true };
}

export async function logoutAction(): Promise<void> {
  const cookieStore = await cookies();
  cookieStore.delete(AUTH_COOKIE_NAME);
  redirect("/login");
}
