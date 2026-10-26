import { Link } from "react-router-dom";
import { EmptyState } from "../components/Loader";

export default function NotFound() {
  return (
    <EmptyState emoji="🧭" title="This page doesn't exist">
      <Link to="/" className="btn btn-primary">
        Go home
      </Link>
    </EmptyState>
  );
}
