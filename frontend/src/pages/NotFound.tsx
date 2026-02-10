import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-slate-100 p-4 text-center">
      <h1 className="text-4xl font-bold text-slate-900">404</h1>
      <p className="mt-2 text-sm text-slate-600">The page you requested was not found.</p>
      <Link to="/dashboard" className="mt-6 rounded bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-700">
        Go to Dashboard
      </Link>
    </div>
  );
}
