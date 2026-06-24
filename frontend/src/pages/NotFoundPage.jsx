import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="font-display text-3xl text-paper-100 mb-2">404</div>
      <p className="text-sm text-paper-500 mb-4">This page doesn't exist in the console.</p>
      <Link to="/" className="text-sm text-amber-400 hover:underline">
        Back to overview
      </Link>
    </div>
  );
}
