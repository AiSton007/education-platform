import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { register, Role } from "../api";

export function RegisterPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    email: "",
    password: "",
    full_name: "",
    department: "",
    position: "",
    role: "employee" as Role,
  });
  const [ok, setOk] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await register(form);
      setOk(true);
      setTimeout(() => navigate("/login"), 1200);
    } catch (err: unknown) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError(((err as any)?.response?.data?.error?.message) ?? "Registration failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h2>Регистрация</h2>
      {ok && <div className="ok">Готово, перенаправляем на вход…</div>}
      <form onSubmit={onSubmit}>
        <label>Email</label>
        <input type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <label>Имя</label>
        <input required value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
        <label>Отдел</label>
        <input value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} />
        <label>Должность</label>
        <input value={form.position} onChange={(e) => setForm({ ...form, position: e.target.value })} />
        <label>Роль</label>
        <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as Role })}>
          <option value="employee">employee</option>
          <option value="manager">manager</option>
          <option value="admin">admin</option>
        </select>
        <label>Пароль</label>
        <input
          type="password"
          required
          minLength={8}
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
        />
        {error && <div className="error">{error}</div>}
        <button className="btn" type="submit" disabled={busy} style={{ marginTop: "1rem" }}>
          {busy ? "..." : "Создать аккаунт"}
        </button>
      </form>
    </div>
  );
}
