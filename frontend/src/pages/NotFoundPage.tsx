import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <section>
      <h2>404</h2>
      <p>The requested page could not be found.</p>
      <Link to="/">Back to dashboard</Link>
    </section>
  );
}
