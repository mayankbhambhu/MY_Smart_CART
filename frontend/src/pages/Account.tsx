import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { EmptyState } from "../components/Loader";
import { api } from "../lib/api";
import type { Address } from "../lib/types";

export default function Account() {
  const { user, setUser, logout, requireLogin } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState(user?.name ?? "");
  const [saved, setSaved] = useState(false);
  const [addresses, setAddresses] = useState<Address[]>([]);

  useEffect(() => {
    if (!user) return;
    setName(user.name ?? "");
    api.addresses().then(setAddresses);
  }, [user]);

  if (!user) {
    return (
      <EmptyState emoji="👤" title="You're not logged in">
        <button className="btn btn-primary" onClick={() => requireLogin()}>
          Login
        </button>
      </EmptyState>
    );
  }

  return (
    <div className="page narrow">
      <h1 className="page-title">My account</h1>
      <section className="card">
        <p className="muted small">Logged in as +91 {user.phone}</p>
        <form
          className="row-gap"
          onSubmit={async (e) => {
            e.preventDefault();
            setUser(await api.updateMe({ name: name.trim() || null }));
            setSaved(true);
          }}
        >
          <label className="field grow">
            <span>Name</span>
            <input value={name} onChange={(e) => (setName(e.target.value), setSaved(false))} maxLength={100} />
          </label>
          <button className="btn btn-primary">{saved ? "Saved ✓" : "Save"}</button>
        </form>
      </section>
      <nav className="card account-links">
        <Link to="/orders">📦 My orders</Link>
        {user.role === "staff" && <Link to="/staff">🏪 Store staff dashboard</Link>}
      </nav>
      <section className="card">
        <h3>Saved addresses</h3>
        {addresses.length === 0 && <p className="muted small">Addresses you add at checkout appear here.</p>}
        {addresses.map((a) => (
          <div key={a.id} className="row-between address-row">
            <span>
              <strong>{a.label}</strong>
              <span className="muted small block">
                {[a.line1, a.landmark, a.city, a.pincode].filter(Boolean).join(", ")}
              </span>
            </span>
            <button
              className="link-btn danger"
              onClick={async () => {
                await api.deleteAddress(a.id);
                setAddresses((list) => list.filter((x) => x.id !== a.id));
              }}
            >
              Delete
            </button>
          </div>
        ))}
      </section>
      <button
        className="btn btn-outline btn-block"
        onClick={() => {
          logout();
          navigate("/");
        }}
      >
        Log out
      </button>
    </div>
  );
}
