import React from 'react';
import { Link } from 'react-router-dom';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import { useTheme } from '../lib/ThemeContext';

export default function LandingPage() {
  const { theme, toggleTheme } = useTheme();
  return (
    <div className="min-h-screen bg-[var(--color-surface)] text-[var(--color-text-primary)]">
      {/* Navigation */}
      <nav className="border-b-[var(--border-width)] border-[var(--color-border)] bg-[var(--color-surface-raised)] sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="font-bold text-xl tracking-tight uppercase flex items-center gap-2">
            <span className="w-6 h-6 bg-[var(--color-primary)] border-[var(--border-width)] border-[var(--color-border)] inline-block shadow-[2px_2px_0px_#121212]"></span>
            GitCompass
          </div>
          <div className="flex items-center gap-4">
            {/* Theme Toggle */}
            <button 
              onClick={toggleTheme}
              className="mr-2 text-[var(--color-text-primary)] hover:text-[var(--color-primary)] transition-colors"
              title="Toggle Theme"
            >
              {theme === 'dark' ? (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
              ) : (
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                </svg>
              )}
            </button>
            <Link to="/login" className="font-bold text-sm hover:underline flex items-center px-4">
              SIGN IN
            </Link>
            <Link to="/register">
              <Button>GET STARTED</Button>
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="max-w-7xl mx-auto px-6 py-24 grid md:grid-cols-2 gap-12 items-center border-b-[var(--border-width)] border-[var(--color-border)]">
        <div>
          <Badge variant="primary" className="mb-6 text-sm">Git History → Engineering Story</Badge>
          <h1 className="text-6xl font-black uppercase leading-[1.1] mb-6 tracking-tighter">
            Understand how your codebase evolved.
          </h1>
          <p className="text-xl text-[var(--color-text-secondary)] mb-8 font-medium max-w-lg">
            GitCompass is an engineering intelligence platform that turns raw repository history into an understandable narrative of architecture, hotspots, and ownership.
          </p>
          <div className="flex gap-4">
            <Link to="/register">
              <Button className="text-lg px-8 py-4">ANALYZE REPOSITORY</Button>
            </Link>
            <Button variant="secondary" className="text-lg px-8 py-4">EXPLORE DEMO</Button>
          </div>
        </div>

        {/* Brutalist Abstract Art / Diagram */}
        <div className="bg-[var(--color-surface-raised)] border-[var(--border-width)] border-[var(--color-border)] shadow-hard-lg p-8 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-32 h-32 bg-[var(--color-primary)] opacity-50 transform translate-x-8 -translate-y-8 rounded-full blur-3xl"></div>
          
          <div className="text-technical text-[var(--color-text-secondary)] mb-4">COMMIT HISTORY</div>
          <div className="font-mono text-sm border-l-4 border-[var(--color-border)] ml-2 pl-4 py-2 space-y-4 relative">
            <div className="relative">
              <div className="absolute -left-[23px] top-1 w-3 h-3 bg-[var(--color-border)] rounded-full"></div>
              <Badge variant="info">AUTH SYSTEM</Badge>
              <div className="text-[var(--color-text-tertiary)] text-xs mt-1">24 commits • 5 files</div>
            </div>
            <div className="relative">
              <div className="absolute -left-[23px] top-1 w-3 h-3 bg-[var(--color-primary)] border border-[var(--color-border)] rounded-full"></div>
              <Badge variant="warning">DATABASE REFACTOR</Badge>
              <div className="text-[var(--color-text-tertiary)] text-xs mt-1">112 commits • 43 files</div>
            </div>
            <div className="relative">
              <div className="absolute -left-[23px] top-1 w-3 h-3 bg-[var(--color-border)] rounded-full"></div>
              <Badge variant="info">API V2</Badge>
              <div className="text-[var(--color-text-tertiary)] text-xs mt-1">86 commits • 12 files</div>
            </div>
            <div className="relative">
              <div className="absolute -left-[23px] top-1 w-3 h-3 bg-[var(--color-border)] rounded-full"></div>
              <Badge variant="info">FRONTEND MIGRATION</Badge>
              <div className="text-[var(--color-text-tertiary)] text-xs mt-1">325 commits • 120 files</div>
            </div>
          </div>
        </div>
      </section>

      {/* Core Features */}
      <section className="max-w-7xl mx-auto px-6 py-24 border-b-[var(--border-width)] border-[var(--color-border)]">
        <h2 className="text-4xl font-black uppercase mb-12">Core Capabilities</h2>
        <div className="grid md:grid-cols-3 gap-8">
          <Card interactive>
            <div className="w-12 h-12 bg-[var(--color-primary)] border-[var(--border-width)] border-[var(--color-border)] mb-6 flex items-center justify-center font-black">01</div>
            <h3 className="text-xl font-bold uppercase mb-3">Evolution Timeline</h3>
            <p className="text-[var(--color-text-secondary)] font-medium">See the exact phases of your project's history, clustered deterministically.</p>
          </Card>
          
          <Card interactive>
            <div className="w-12 h-12 bg-[var(--color-info)] text-white border-[var(--border-width)] border-[var(--color-border)] mb-6 flex items-center justify-center font-black">02</div>
            <h3 className="text-xl font-bold uppercase mb-3">Code Hotspots</h3>
            <p className="text-[var(--color-text-secondary)] font-medium">Identify files with the highest churn and complexity instantly.</p>
          </Card>

          <Card interactive>
            <div className="w-12 h-12 bg-[var(--color-special)] text-white border-[var(--border-width)] border-[var(--color-border)] mb-6 flex items-center justify-center font-black">03</div>
            <h3 className="text-xl font-bold uppercase mb-3">AI Intelligence</h3>
            <p className="text-[var(--color-text-secondary)] font-medium">LLM-generated repository stories and architecture insights based on hard evidence.</p>
          </Card>
        </div>
      </section>

      {/* Final CTA */}
      <section className="bg-[var(--color-primary)] py-32 border-b-[var(--border-width)] border-[var(--color-border)]">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="text-5xl font-black uppercase mb-6 leading-tight">
            Your repository already has a story.
            <br />
            GitCompass helps you read it.
          </h2>
          <div className="mt-10">
            <Link to="/register">
              <button className="bg-[var(--color-surface-raised)] border-4 border-[var(--color-border)] text-2xl font-black uppercase px-12 py-6 shadow-[8px_8px_0px_#121212] hover:translate-y-1 hover:translate-x-1 hover:shadow-[4px_4px_0px_#121212] transition-all">
                Analyze Your Repository
              </button>
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="max-w-7xl mx-auto px-6 py-12 flex justify-between items-center text-sm font-bold uppercase text-[var(--color-text-secondary)]">
        <div>© 2026 GitCompass</div>
        <div className="flex gap-6">
          <a href="#" className="hover:text-[var(--color-text-primary)]">Features</a>
          <a href="#" className="hover:text-[var(--color-text-primary)]">Documentation</a>
          <a href="#" className="hover:text-[var(--color-text-primary)]">Privacy</a>
          <a href="#" className="hover:text-[var(--color-text-primary)]">Terms</a>
        </div>
      </footer>
    </div>
  );
}
