import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Attempt,
  listAttempts,
  listTests,
  listUsers,
  Profile,
  TestSummary,
} from "../api";

export function ManagerAttemptsPage() {
  const [attempts, setAttempts] = useState<Attempt[]>([]);
  const [tests, setTests] = useState<TestSummary[]>([]);
  const [users, setUsers] = useState<Profile[]>([]);
  const [testFilter, setTestFilter] = useState<string>("");
  const [userFilter, setUserFilter] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  async function reload() {
    try {
      const r = await listAttempts({
        test_id: testFilter || undefined,
        user_id: userFilter || undefined,
      });
      setAttempts(r.items);
    } catch (e: unknown) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError((e as any)?.response?.data?.error?.message ?? "Не удалось загрузить прохождения");
    }
  }

  useEffect(() => {
    Promise.all([listTests({ active_only: false }), listUsers()])
      .then(([t, u]) => {
        setTests(t.items);
        setUsers(u.items);
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    reload();
  }, [testFilter, userFilter]);

  const testTitleById = new Map(tests.map((t) => [t.id, t.title]));
  const userNameById = new Map(users.map((u) => [u.user_id, u.full_name + " (" + u.email + ")"]));

  return (
    <div className="card">
      <h2>Прохождения тестов</h2>
      {error && <div className="error">{error}</div>}
      <div className="filters">
        <label>Тест</label>
        <select value={testFilter} onChange={(e) => setTestFilter(e.target.value)}>
          <option value="">— все —</option>
          {tests.map((t) => (
            <option key={t.id} value={t.id}>{t.title}</option>
          ))}
        </select>
        <label>Сотрудник</label>
        <select value={userFilter} onChange={(e) => setUserFilter(e.target.value)}>
          <option value="">— все —</option>
          {users.map((u) => (
            <option key={u.user_id} value={u.user_id}>{u.full_name}</option>
          ))}
        </select>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>Тест</th>
            <th>Сотрудник</th>
            <th>Статус</th>
            <th>Оценка</th>
            <th>Завершён</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {attempts.map((a) => (
            <tr key={a.id}>
              <td>{testTitleById.get(a.test_id) ?? a.test_id.slice(0, 8)}</td>
              <td>{userNameById.get(a.user_id) ?? a.user_id.slice(0, 8)}</td>
              <td>{a.status}</td>
              <td>{a.score === null ? "—" : a.score.toFixed(1)}</td>
              <td>{a.completed_at ? new Date(a.completed_at).toLocaleString() : "—"}</td>
              <td>
                <Link className="btn secondary" to={`/manage/attempts/${a.id}`}>Открыть</Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {attempts.length === 0 && <p className="muted">Прохождений по выбранным фильтрам нет.</p>}
    </div>
  );
}
