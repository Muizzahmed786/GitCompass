/**
 * Login — GitHub OAuth sign-in page.
 *
 * Clean, centered layout with a single call-to-action.
 * Calls supabase.auth.signInWithOAuth({ provider: "github" }).
 */

import { useState } from "react";
import { supabase } from "../lib/supabase";

export default function Login() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleGitHubLogin = async () => {
    setLoading(true);
    setError(null);

    const { error: authError } = await supabase.auth.signInWithOAuth({
      provider: "github",
      options: {
        redirectTo: window.location.origin,
      },
    });

    if (authError) {
      setError(authError.message);
      setLoading(false);
    }
    // On success, the browser redirects to GitHub — no need to handle here
  };

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center px-4">
      <div className="animate-fade-in w-full max-w-sm">
        {/* Brand */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-primary-100 rounded-2xl mb-5">
            <svg
              className="w-7 h-7 text-primary-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
              />
            </svg>
          </div>
          <h1 className="text-2xl font-semibold text-text-primary tracking-tight">
            GIT Compass
          </h1>
          <p className="mt-2 text-sm text-text-secondary leading-relaxed">
            Transform your repository's Git history
            <br />
            into analytical intelligence.
          </p>
        </div>

        {/* Login card */}
        <div className="card-flat p-6">
          <button
            onClick={handleGitHubLogin}
            disabled={loading}
            className="
              w-full flex items-center justify-center gap-3
              px-4 py-3 rounded-lg
              bg-text-primary text-white
              hover:bg-gray-800
              disabled:opacity-50 disabled:cursor-not-allowed
              transition-colors duration-150
              text-sm font-medium
              cursor-pointer
            "
          >
            {loading ? (
              <span className="animate-pulse-soft">Redirecting to GitHub…</span>
            ) : (
              <>
                {/* GitHub icon */}
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 0C5.374 0 0 5.373 0 12c0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23A11.509 11.509 0 0112 5.803c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576C20.566 21.797 24 17.3 24 12c0-6.627-5.373-12-12-12z" />
                </svg>
                Continue with GitHub
              </>
            )}
          </button>

          {error && (
            <div className="mt-4 p-3 rounded-md bg-error-light text-error text-xs text-center">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <p className="mt-6 text-center text-xs text-text-tertiary">
          We only request read access to your public profile.
        </p>
      </div>
    </div>
  );
}
