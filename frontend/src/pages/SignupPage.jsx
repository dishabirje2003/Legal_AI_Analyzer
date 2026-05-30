import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import PublicNavbar from '../components/layout/PublicNavbar.jsx';
import { Button } from '../components/ui/Button.jsx';
import { Input } from '../components/ui/Input.jsx';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card.jsx';
import { useAuth } from '../contexts/AuthContext.jsx';
import { isSupabaseConfigured } from '../lib/supabase.js';

function isValidEmail(v) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim());
}

const MIN_PASSWORD = 8;

export default function SignupPage() {
  const navigate = useNavigate();
  const { signUp } = useAuth();

  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState(/** @type {Record<string, string>} */ ({}));
  const [submitError, setSubmitError] = useState('');
  const [loading, setLoading] = useState(false);

  function validate() {
    const next = {};
    if (!name.trim()) next.name = 'Name is required';
    if (!email.trim()) next.email = 'Email is required';
    else if (!isValidEmail(email)) next.email = 'Enter a valid email';
    if (!password) next.password = 'Password is required';
    else if (password.length < MIN_PASSWORD)
      next.password = `Use at least ${MIN_PASSWORD} characters`;
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
      await signUp(name.trim(), email.trim(), password);
      navigate('/login', { replace: true, state: { fromSignup: true, email: email.trim() } });
    } catch (err) {
      const msg =
        err && typeof err === 'object' && 'message' in err
          ? String(err.message)
          : 'Could not create account. Try again.';
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
            <CardTitle className="text-xl">Create account</CardTitle>
            <p className="text-sm font-normal text-slate-600">
              Only what we need: your name, email, and password.
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
            <form onSubmit={handleSubmit} className="space-y-5" noValidate>
              <Input
                name="name"
                type="text"
                autoComplete="name"
                label="Name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                error={errors.name}
              />
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
                autoComplete="new-password"
                label="Password"
                hint={`At least ${MIN_PASSWORD} characters`}
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
                Sign up
              </Button>
            </form>
            <p className="mt-6 text-center text-sm text-slate-600">
              Already have an account?{' '}
              <Link
                to="/login"
                className="font-medium text-blue-600 transition-colors hover:text-blue-700"
              >
                Log in
              </Link>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
