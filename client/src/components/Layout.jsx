import React, { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';
import { Link, useLocation } from 'react-router-dom';
import CommandPalette from './search/CommandPalette';
import { useTheme } from '../lib/ThemeContext';

export default function Layout({ children, user }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const location = useLocation();
  const { theme, toggleTheme } = useTheme();

  const handleSignOut = async () => {
    await supabase.auth.signOut();
  };

  const avatarUrl = user?.user_metadata?.avatar_url;
  const displayName =
    user?.user_metadata?.full_name ||
    user?.user_metadata?.user_name ||
    user?.email ||
    "User";

  // Check if we are inside a repository context
  const isRepoContext = location.pathname.includes('/repository/');
  const repoId = isRepoContext ? location.pathname.split('/')[2] : null;

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setPaletteOpen(true);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="min-h-screen bg-[var(--color-surface)] flex flex-col md:flex-row">
      <CommandPalette isOpen={paletteOpen} onClose={() => setPaletteOpen(false)} />
      
      {/* ── Sidebar (Mobile Toggle) ───────────────────────── */}
      <button 
        className="md:hidden fixed bottom-4 right-4 z-50 bg-[var(--color-primary)] border-2 border-[var(--color-border)] p-4 shadow-hard rounded-full"
        onClick={() => setSidebarOpen(!sidebarOpen)}
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="square" strokeLinejoin="miter" strokeWidth={3} d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      {/* ── Sidebar ─────────────────────────────────────── */}
      <aside className={`
        fixed inset-y-0 left-0 z-40 w-64 bg-[var(--color-surface-raised)] border-r-2 border-[var(--color-border)] transform transition-transform duration-200 ease-in-out md:translate-x-0 md:static flex flex-col
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        {/* Brand */}
        <div className="h-16 flex items-center px-6 border-b-2 border-[var(--color-border)]">
          <Link to="/dashboard" className="font-black text-xl tracking-tight uppercase flex items-center gap-2">
            <span className="w-6 h-6 bg-[var(--color-primary)] border-2 border-[var(--color-border)] inline-block shadow-[2px_2px_0px_#121212]"></span>
            GitCompass
          </Link>
        </div>

        {/* Global Navigation */}
        <div className="flex-1 overflow-y-auto py-4 flex flex-col gap-1">
          <div className="px-6 py-2 text-xs font-black uppercase text-[var(--color-text-tertiary)] tracking-widest">
            Overview
          </div>
          <Link to="/dashboard" className={`px-6 py-3 font-bold uppercase text-sm border-l-4 ${location.pathname === '/dashboard' ? 'border-[var(--color-primary)] bg-[var(--color-surface)] text-[var(--color-text-primary)]' : 'border-transparent text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)]'}`}>
            Repositories
          </Link>
          
          {isRepoContext && (
            <>
              <div className="px-6 py-2 mt-4 text-xs font-black uppercase text-[var(--color-text-tertiary)] tracking-widest">
                Repository
              </div>
              <Link to={`/repository/${repoId}`} className={`px-6 py-3 font-bold uppercase text-sm border-l-4 ${location.pathname === `/repository/${repoId}` ? 'border-[var(--color-info)] bg-[var(--color-surface)] text-[var(--color-text-primary)]' : 'border-transparent text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)]'}`}>
                Overview
              </Link>
              <Link to={`/repository/${repoId}/evolution`} className={`px-6 py-3 font-bold uppercase text-sm border-l-4 ${location.pathname.includes('/evolution') ? 'border-[var(--color-info)] bg-[var(--color-surface)] text-[var(--color-text-primary)]' : 'border-transparent text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)]'}`}>
                Evolution
              </Link>
              <Link to={`/repository/${repoId}/architecture`} className={`px-6 py-3 font-bold uppercase text-sm border-l-4 ${location.pathname.includes('/architecture') ? 'border-[var(--color-info)] bg-[var(--color-surface)] text-[var(--color-text-primary)]' : 'border-transparent text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)]'}`}>
                Architecture
              </Link>
              <Link to={`/repository/${repoId}/hotspots`} className={`px-6 py-3 font-bold uppercase text-sm border-l-4 ${location.pathname.includes('/hotspots') ? 'border-[var(--color-info)] bg-[var(--color-surface)] text-[var(--color-text-primary)]' : 'border-transparent text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)]'}`}>
                Hotspots
              </Link>
              <Link to={`/repository/${repoId}/contributors`} className={`px-6 py-3 font-bold uppercase text-sm border-l-4 ${location.pathname.includes('/contributors') ? 'border-[var(--color-info)] bg-[var(--color-surface)] text-[var(--color-text-primary)]' : 'border-transparent text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)]'}`}>
                Contributors
              </Link>
              <Link to={`/repository/${repoId}/ai`} className={`px-6 py-3 font-bold uppercase text-sm border-l-4 ${location.pathname.includes('/ai') ? 'border-[var(--color-info)] bg-[var(--color-surface)] text-[var(--color-text-primary)]' : 'border-transparent text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)]'}`}>
                AI Insights
              </Link>
            </>
          )}

          <div className="mt-auto pt-4 border-t-2 border-[var(--color-border)] px-4">
            <button className="w-full text-left px-4 py-3 font-bold uppercase text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)] flex items-center gap-3">
              Settings
            </button>
            <button className="w-full text-left px-4 py-3 font-bold uppercase text-sm text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)] flex items-center gap-3">
              Help
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main Content Area ───────────────────────────── */}
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        
        {/* ── Top Navbar ──────────────────────────────── */}
        <header className="h-16 bg-[var(--color-surface-raised)] border-b-2 border-[var(--color-border)] flex items-center justify-between px-6 shrink-0 sticky top-0 z-30">
          
          {/* Global Search (Command Palette entry) */}
          <div className="flex-1 max-w-md">
            <button 
              onClick={() => setPaletteOpen(true)}
              className="w-full bg-[var(--color-surface)] border-2 border-[var(--color-border)] text-left px-4 py-2 text-sm text-[var(--color-text-secondary)] font-mono flex items-center justify-between hover:shadow-[2px_2px_0px_#121212] transition-shadow"
            >
              <span>Search GitCompass...</span>
              <kbd className="hidden sm:inline-block font-black px-2 py-1 bg-[var(--color-surface-raised)] border-2 border-[var(--color-border)] shadow-[1px_1px_0px_#121212] text-xs">⌘K</kbd>
            </button>
          </div>

          {/* User & Actions */}
          <div className="flex items-center gap-6 ml-4">
            
            {/* Theme Toggle */}
            <button 
              onClick={toggleTheme}
              className="relative text-[var(--color-text-primary)] hover:text-[var(--color-primary)] transition-colors"
              title="Toggle Theme"
            >
              {theme === 'dark' ? (
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
              ) : (
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                </svg>
              )}
            </button>

            {/* Notifications Toggle */}
            <div className="relative">
              <button 
                onClick={() => setNotificationsOpen(!notificationsOpen)}
                className="relative text-[var(--color-text-primary)] hover:text-[var(--color-primary)] transition-colors p-1"
                title="Notifications"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="square" strokeLinejoin="miter" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                </svg>
                <span className="absolute top-0 right-0 w-2.5 h-2.5 bg-[var(--color-warning)] border-2 border-[var(--color-surface-raised)] rounded-full"></span>
              </button>

              {/* Notifications Dropdown */}
              {notificationsOpen && (
                <div className="absolute right-0 mt-2 w-80 bg-[var(--color-surface-raised)] border-4 border-[var(--color-border)] shadow-[8px_8px_0px_#121212] z-50">
                  <div className="p-4 border-b-4 border-[var(--color-border)] bg-[var(--color-primary)] text-[#121212] flex justify-between items-center">
                    <h4 className="font-black uppercase text-sm">Notifications</h4>
                    <button onClick={() => setNotificationsOpen(false)} className="text-[#121212] font-black p-1 hover:bg-[#121212] hover:text-[#E2FF32]">
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="square" strokeLinejoin="miter" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                  <div className="max-h-64 overflow-y-auto p-0">
                    <div className="p-4 border-b-2 border-[var(--color-border)] hover:bg-[var(--color-surface-hover)] cursor-pointer">
                      <p className="text-sm font-bold">Analysis Complete</p>
                      <p className="text-xs text-[var(--color-text-secondary)] mt-1">GitCompass repository has been successfully mined.</p>
                      <p className="text-[10px] text-[var(--color-text-tertiary)] font-mono mt-2">Just now</p>
                    </div>
                    <div className="p-4 hover:bg-[var(--color-surface-hover)] cursor-pointer">
                      <p className="text-sm font-bold">Welcome to GitCompass</p>
                      <p className="text-xs text-[var(--color-text-secondary)] mt-1">Your engineering intelligence dashboard is ready.</p>
                      <p className="text-[10px] text-[var(--color-text-tertiary)] font-mono mt-2">1 hour ago</p>
                    </div>
                  </div>
                  <div className="p-2 border-t-4 border-[var(--color-border)] text-center">
                    <button className="text-xs font-black uppercase text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]">Mark all as read</button>
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center gap-3 border-l-2 border-[var(--color-border)] pl-6">
              <div className="hidden sm:block text-right">
                <div className="text-sm font-bold uppercase">{displayName}</div>
                <button onClick={handleSignOut} className="text-xs font-mono text-[var(--color-text-secondary)] hover:text-[var(--color-warning)] uppercase tracking-wider">
                  Sign out
                </button>
              </div>
              {avatarUrl ? (
                <img src={avatarUrl} alt={displayName} className="w-10 h-10 border-2 border-[var(--color-border)] shadow-[2px_2px_0px_#121212]" />
              ) : (
                <div className="w-10 h-10 border-2 border-[var(--color-border)] bg-[var(--color-primary)] shadow-[2px_2px_0px_#121212] flex items-center justify-center font-black">
                  {displayName.charAt(0).toUpperCase()}
                </div>
              )}
            </div>
          </div>
        </header>

        {/* ── Page Content ────────────────────────────── */}
        <main className="flex-1 overflow-auto p-4 sm:p-8">
          <div className="max-w-7xl mx-auto">
            {children}
          </div>
        </main>
      </div>

    </div>
  );
}
