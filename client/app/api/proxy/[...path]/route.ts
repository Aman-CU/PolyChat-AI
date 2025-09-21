import { NextRequest, NextResponse } from "next/server";
import { getToken } from "next-auth/jwt";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function handler(
  req: NextRequest,
  ctx: { params: Promise<{ path: string[] }> }
) {
  const { path } = await ctx.params;
  const targetPath = Array.isArray(path) ? path.join("/") : String(path || "");
  const url = `${API_BASE}/${targetPath}`;

  // Clone request init
  const headers: Record<string, string> = {};
  req.headers.forEach((v, k) => {
    // skip host-related headers that don't make sense cross-origin
    if (["host", "connection"].includes(k.toLowerCase())) return;
    headers[k] = v;
  });

  // Attach NextAuth raw JWT if present
  try {
    const token = await getToken({ req, raw: true, secret: process.env.NEXTAUTH_SECRET });
    if (token) headers["authorization"] = `Bearer ${token}`;
  } catch {}

  // Ensure a stable guest id via cookie and forward as header for server scoping
  let guestId = req.cookies.get("guest_id")?.value;
  if (!guestId) {
    try {
      guestId = crypto.randomUUID();
    } catch {
      guestId = Math.random().toString(36).slice(2) + Date.now().toString(36);
    }
  }
  if (guestId) headers["x-guest-id"] = guestId;

  const body = ["GET", "HEAD"].includes(req.method) ? undefined : await req.text();

  const res = await fetch(url, {
    method: req.method,
    headers,
    body,
    redirect: "manual",
  });

  const responseHeaders = new Headers();
  res.headers.forEach((v, k) => responseHeaders.set(k, v));

  const response = new NextResponse(res.body, {
    status: res.status,
    headers: responseHeaders,
  });
  // Persist guest_id cookie (httpOnly false so browser tools can inspect if needed; adjust as desired)
  if (guestId && !req.cookies.get("guest_id")?.value) {
    response.cookies.set("guest_id", guestId, {
      path: "/",
      sameSite: "lax",
      httpOnly: false,
      secure: false,
      maxAge: 60 * 60 * 24 * 365, // 1 year
    });
  }
  return response;
}

export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const PATCH = handler;
export const DELETE = handler;
export const OPTIONS = handler;
