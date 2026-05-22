import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../api";

export function LoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const tokens = await login(email, password);
      localStorage.setItem("access_token", tokens.access_token);
      localStorage.setItem("refresh_token", tokens.refresh_token);
      navigate("/tests");
    } catch (err: unknown) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError(((err as any)?.response?.data?.error?.message) ?? "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h2>Вход</h2>
      <form onSubmit={onSubmit}>
        <label>Email</label>
        <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        <label>Пароль</label>
        <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        {error && <div className="error">{error}</div>}
        <button className="btn" type="submit" disabled={busy} style={{ marginTop: "1rem" }}>
          {busy ? "..." : "Войти"}
        </button>
      </form>
    </div>
  );
}
