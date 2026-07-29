/**
 * Layout — Application shell.
 *
 * Clean, minimal layout with:
 * - Top navigation bar with branding and user controls
 * - Generous white-space content area
 * - Light background (#FAFBFC)
 */

import { supabase } from "../lib/supabase";

export default function Layout({ children, user }) {
  const handleSignOut = async () => {
    await supabase.auth.signOut();
  };

  const avatarUrl = user?.user_metadata?.avatar_url;
  const displayName =
    user?.user_metadata?.full_name ||
    user?.user_metadata?.user_name ||
    user?.email ||
    "User";

  return (
    <div className="min-h-screen bg-surface">
      {/* ── Navigation ──────────────────────────────────── */}
      <nav className="bg-surface-raised border-b border-border sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Brand */}
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-8 h-8 bg-primary-100 rounded-lg">
                <svg
                  className="w-4.5 h-4.5 text-primary-600"
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
              <span className="text-lg font-semibold text-text-primary tracking-tight">
                GIT Compass
              </span>
            </div>

            {/* User controls */}
            <div className="flex items-center gap-4">
              <span className="text-sm text-text-secondary hidden sm:block">
                {displayName}
              </span>
              {avatarUrl && (
                <img
                  src={avatarUrl}
                  alt={displayName}
                  className="w-8 h-8 rounded-full ring-2 ring-border"
                />
              )}
              <button
                onClick={handleSignOut}
                className="
                  text-sm text-text-secondary hover:text-text-primary
                  px-3 py-1.5 rounded-md
                  hover:bg-surface-hover
                  transition-colors duration-150
                  cursor-pointer
                "
              >
                Sign out
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* ── Content ─────────────────────────────────────── */}
      <main className="max-w-6xl mx-auto px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  );
}
