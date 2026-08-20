import React, { useState } from "react";
import { supabase } from "../lib/supabase";
import { Link, useNavigate } from "react-router-dom";
import Button from "../components/ui/Button";
import Input from "../components/ui/Input";
import Card from "../components/ui/Card";
import Badge from "../components/ui/Badge";

export default function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  
  const navigate = useNavigate();

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const { error } = await supabase.auth.signUp({
      email,
      password,
    });

    if (error) {
      setError(error.message);
    } else {
      setSuccess(true);
    }
    setLoading(false);
  };

  const handleGithubLogin = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "github",
      options: { redirectTo: window.location.origin + "/dashboard" },
    });
    if (error) setError(error.message);
  };

  return (
    <div className="min-h-screen bg-[var(--color-surface)] flex flex-col items-center justify-center p-6">
      <Link to="/" className="mb-8 font-bold text-2xl tracking-tight uppercase flex items-center gap-2">
        <span className="w-8 h-8 bg-[var(--color-primary)] border-[var(--border-width)] border-[var(--color-border)] inline-block shadow-[2px_2px_0px_#121212]"></span>
        GitCompass
      </Link>

      <Card className="w-full max-w-md p-8">
        <div className="mb-8">
          <Badge variant="primary" className="mb-4">START YOUR STORY</Badge>
          <h2 className="text-3xl font-black uppercase tracking-tight">Create Account</h2>
          <p className="text-[var(--color-text-secondary)] mt-2 font-medium">Join GitCompass to analyze your repositories.</p>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-[var(--color-warning)] text-white border-[var(--border-width)] border-[var(--color-border)] font-bold text-sm">
            {error}
          </div>
        )}

        {success ? (
          <div className="mb-6 p-6 bg-[var(--color-success)] text-[var(--color-border)] border-[var(--border-width)] border-[var(--color-border)] font-bold text-center">
            Registration successful! Please check your email to verify your account.
          </div>
        ) : (
          <form onSubmit={handleRegister} className="space-y-6">
            <div>
              <label className="block text-sm font-bold uppercase mb-2">Email Address</label>
              <Input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
              />
            </div>
            
            <div>
              <label className="block text-sm font-bold uppercase mb-2">Password</label>
              <Input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </div>

            <Button type="submit" className="w-full py-4 text-lg" disabled={loading}>
              {loading ? "CREATING..." : "CREATE ACCOUNT"}
            </Button>
          </form>
        )}

        <div className="mt-8 relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t-[var(--border-width)] border-[var(--color-border)]"></div>
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-4 bg-[var(--color-surface-raised)] font-bold uppercase text-[var(--color-text-secondary)]">Or</span>
          </div>
        </div>

        <div className="mt-8">
          <button 
            onClick={handleGithubLogin}
            className="w-full p-4 border-[var(--border-width)] border-[var(--color-border)] bg-[var(--color-surface)] hover:bg-[var(--color-surface-hover)] font-bold uppercase flex items-center justify-center gap-3 transition-colors shadow-hard"
          >
            <svg viewBox="0 0 24 24" className="w-6 h-6" fill="currentColor">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
            </svg>
            Continue with GitHub
          </button>
        </div>
        
        <div className="mt-8 text-center text-sm font-bold">
          Already have an account? <Link to="/login" className="text-[var(--color-info)] hover:underline">SIGN IN</Link>
        </div>
      </Card>
    </div>
  );
}
