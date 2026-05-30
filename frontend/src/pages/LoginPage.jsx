import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import PublicNavbar from '../components/layout/PublicNavbar.jsx';
import { Button } from '../components/ui/Button.jsx';
import { Input } from '../components/ui/Input.jsx';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card.jsx';
import { useAuth } from '../contexts/AuthContext.jsx';
import { isSupabaseConfigured } from '../lib/supabase.js';

function isValidEmail(v) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim());
}

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { signIn } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState(/** @type {Record<string, string>} */ ({}));
  const [submitError, setSubmitError] = useState('');
  const [loading, setLoading] = useState(false);

  const fromSignup = Boolean(location.state?.fromSignup);
  const signupEmail =
    typeof location.state?.email === 'string' ? location.state.email : '';

  const from = location.state?.from;
  const redirectTo =
    typeof from === 'string' && from.startsWith('/') && from !== '/login' && from !== '/signup'
      ? from
      : '/dashboard';

  function validate() {
    const next = {};
    if (!email.trim()) next.email = 'Email is required';
    else if (!isValidEmail(email)) next.email = 'Enter a valid email';
    if (!password) next.password = 'Password is required';
    setErrors(next);
    return Object.keys(next).length === 0;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSubmitError('');
    if (!isSupabaseConfigured) {
      setSubmitError(
        'Supabase is not configured. Add VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY to frontend/.env and restart the dev server.',
      );
      return;
    }
    if (!validate()) return;
    setLoading(true);
    try {
      await signIn(email.trim(), password);
      navigate(redirectTo, { replace: true });
    } catch (err) {
      const msg =
        err && typeof err === 'object' && 'message' in err
          ? String(err.message)
          : 'Could not sign in. Try again.';
      setSubmitError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <PublicNavbar />
      <div className="mx-auto flex min-h-[calc(100vh-4rem)] max-w-md flex-col justify-center px-4 py-12 sm:px-6">
        <Card className="border-slate-200/80 shadow-lg shadow-slate-200/40 transition-shadow duration-300">
          <CardHeader className="space-y-1">
            <CardTitle className="text-xl">Log in</CardTitle>
            <p className="text-sm font-normal text-slate-600">
              Welcome back. Enter your credentials to open your workspace.
            </p>
          </CardHeader>
          <CardContent className="px-6 pb-8 pt-0">
            {!isSupabaseConfigured ? (
              <p className="mb-5 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
                Add <code className="rounded bg-amber-100/80 px-1">VITE_SUPABASE_URL</code> and{' '}
                <code className="rounded bg-amber-100/80 px-1">VITE_SUPABASE_ANON_KEY</code> to{' '}
                <code className="rounded bg-amber-100/80 px-1">frontend/.env</code> and restart{' '}
                <code className="rounded bg-amber-100/80 px-1">npm run dev</code>.
              </p>
            ) : null}
            {fromSignup ? (
              <p className="mb-5 rounded-lg border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-900">
                Account created. {signupEmail ? <>Log in with <strong>{signupEmail}</strong>.</> : 'Please log in.'}
              </p>
            ) : null}
            <form onSubmit={handleSubmit} className="space-y-5" noValidate>
              <Input
                name="email"
                type="email"
                autoComplete="email"
                label="Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                error={errors.email}
              />
              <Input
                name="password"
                type="password"
                autoComplete="current-password"
                label="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                error={errors.password}
              />
              {submitError ? (
                <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
                  {submitError}
                </p>
              ) : null}
              <Button
                type="submit"
                className="w-full"
                loading={loading}
                disabled={!isSupabaseConfigured}
              >
                Log in
              </Button>
            </form>
            <p className="mt-6 text-center text-sm text-slate-600">
              Don&apos;t have an account?{' '}
              <Link
                to="/signup"
                className="font-medium text-blue-600 transition-colors hover:text-blue-700"
              >
                Sign up
              </Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
