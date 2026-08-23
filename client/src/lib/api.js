/**
 * Thin fetch wrapper for calling the FastAPI backend.
 *
 * CRITICAL CONSTRAINT: All paths MUST be relative (e.g., "/api/health").
 * Never hardcode "http://localhost:8000" — the Vite dev server proxies
 * /api requests to the backend automatically.
 *
 * Automatically attaches the Supabase session JWT as a Bearer token
 * so FastAPI can create a user-scoped Supabase client with RLS enforcement.
 */

import { supabase } from "./supabase";

/**
 * Make an authenticated API request to the backend.
 *
 * @param {string} path    Relative path, e.g. "/api/health"
 * @param {object} options Fetch options (method, body, headers, etc.)
 * @returns {Promise<any>} Parsed JSON response
 */
export async function api(path, options = {}) {
  // Safety check: prevent accidental absolute URLs
  if (path.startsWith("http")) {
    throw new Error(
      `api() received an absolute URL: "${path}". ` +
        `Use relative paths like "/api/health" instead.`
    );
  }

  // Get the current session JWT
  const {
    data: { session },
  } = await supabase.auth.getSession();

  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  // Attach Bearer token if the user is authenticated
  if (session?.access_token) {
    headers["Authorization"] = `Bearer ${session.access_token}`;
  }

  const response = await fetch(path, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`API ${response.status}: ${errorBody}`);
  }

  return response.json();
}

/**
 * Convenience methods matching common HTTP verbs.
 */
api.get = (path) => api(path, { method: "GET" });

api.post = (path, body) =>
  api(path, { method: "POST", body: body ? JSON.stringify(body) : undefined });

api.put = (path, body) =>
  api(path, { method: "PUT", body: body ? JSON.stringify(body) : undefined });

api.delete = (path) => api(path, { method: "DELETE" });

/**
 * AI Endpoints
 */
api.getAISummary = (repoId, payload = {}) => api.post(`/api/ai/summary/${repoId}`, payload);
api.getAIShifts = (repoId, payload = {}) => api.post(`/api/ai/shifts/${repoId}`, payload);
api.getAIStory = (repoId, payload = {}) => api.post(`/api/ai/story/${repoId}`, payload);
api.askAIChat = (repoId, history) => api.post(`/api/ai/chat/${repoId}`, { history });

