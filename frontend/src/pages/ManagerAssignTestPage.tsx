import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Assignment,
  assignTest,
  getTest,
  listAssignmentsForTest,
  listUsers,
  Profile,
  revokeAssignment,
  TestAdmin,
} from "../api";

export function ManagerAssignTestPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [test, setTest] = useState<TestAdmin | null>(null);
  const [users, setUsers] = useState<Profile[]>([]);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [dueDate, setDueDate] = useState("");

  async function reload() {
    try {
      const [t, u, a] = await Promise.all([
        getTest(id),
        listUsers(),
        listAssignmentsForTest(id),
      ]);
      setTest(t as TestAdmin);
      setUsers(u.items.filter((p) => p.is_active && p.role === "employee"));
      setAssignments(a);
    } catch (e: unknown) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError((e as any)?.response?.data?.error?.message ?? "Не удалось загрузить данные");
    }
  }

  useEffect(() => {
    if (id) reload();
  }, [id]);

  function toggle(uid: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(uid)) next.delete(uid);
      else next.add(uid);
      return next;
    });
  }

  async function onAssign() {
    if (selected.size === 0) return;
    setBusy(true);
    setError(null);
    try {
      await assignTest({
        test_id: id,
        user_ids: Array.from(selected),
        due_date: dueDate ? new Date(dueDate).toISOString() : null,
      });
      setSelected(new Set());
      setDueDate("");
      await reload();
    } catch (e: unknown) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError((e as any)?.response?.data?.error?.message ?? "Не удалось назначить тест");
    } finally {
      setBusy(false);
    }
  }

  async function onRevoke(assignmentId: string) {
    if (!window.confirm("Снять назначение?")) return;
    try {
      await revokeAssignment(assignmentId);
      await reload();
    } catch (e: unknown) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError((e as any)?.response?.data?.error?.message ?? "Не удалось снять назначение");
    }
  }

  const assignedUserIds = new Set(assignments.map((a) => a.user_id));

  return (
    <div className="card">
      <button className="btn secondary small" onClick={() => navigate("/manage/tests")}>
        ← К списку тестов
      </button>
      <h2>Назначение теста</h2>
      {test && (
        <div className="meta">
          <div><strong>Тест:</strong> {test.title}</div>
          <div className="muted">{test.questions.length} вопросов</div>
        </div>
      )}
      {error && <div className="error">{error}</div>}

      <h3>Назначить сотрудникам</h3>
      <label>Срок выполнения (опционально)</label>
      <input
        type="datetime-local"
        value={dueDate}
        onChange={(e) => setDueDate(e.target.value)}
        style={{ maxWidth: "320px" }}
      />
      <table className="table">
        <thead>
          <tr>
            <th></th>
            <th>Сотрудник</th>
            <th>Email</th>
            <th>Подразделение</th>
            <th>Статус назначения</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => {
            const existing = assignments.find((a) => a.user_id === u.user_id);
            return (
              <tr key={u.user_id}>
                <td>
                  {!existing && (
                    <input
                      type="checkbox"
                      checked={selected.has(u.user_id)}
                      onChange={() => toggle(u.user_id)}
                    />
                  )}
                </td>
                <td>{u.full_name}</td>
                <td>{u.email}</td>
                <td>{u.department ?? "—"}</td>
                <td>
                  {existing ? (
                    <>
                      <span>{existing.status}</span>{" "}
                      <button
                        className="btn secondary danger small"
                        onClick={() => onRevoke(existing.id)}
                      >
                        Снять
                      </button>
                    </>
                  ) : assignedUserIds.has(u.user_id) ? (
                    "назначен"
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <button
        className="btn"
        onClick={onAssign}
        disabled={busy || selected.size === 0}
        style={{ marginTop: "1rem" }}
      >
        {busy ? "Назначаем…" : `Назначить (${selected.size})`}
      </button>
    </div>
  );
}
