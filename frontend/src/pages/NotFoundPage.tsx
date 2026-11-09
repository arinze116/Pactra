import { Link } from "react-router-dom";
import { PublicFooter } from "../components/PublicFooter";

export function NotFoundPage({ authenticated = false }: { authenticated?: boolean }) {
  const content = (
    <div>
      <p className="text-sm font-medium text-pactra-300">404</p>
      <h1 className="mt-3 text-3xl font-medium">This page does not exist</h1>
      <p className="mt-2 text-sm text-ink-500">Return to a known part of the Pactra sandbox.</p>
      <Link className="action-primary mt-6" to={authenticated ? "/app" : "/"}>
        {authenticated ? "Go to overview" : "Go home"}
      </Link>
    </div>
  );

  if (authenticated) {
    return <div className="grid min-h-[60vh] place-items-center text-center">{content}</div>;
  }

  return (
    <div className="flex min-h-screen flex-col bg-canvas text-ink-950">
      <main className="grid flex-1 place-items-center px-5 py-16 text-center">{content}</main>
      <PublicFooter />
    </div>
  );
}
