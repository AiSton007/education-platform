import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { deleteTest, listTests, TestSummary, updateTest } from "../api";

export function ManagerTestsPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<TestSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  function reload() {
    setError(null);
    listTests({ active_only: false })
      .then((r) => setItems(r.items))
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .catch((e: any) => setError(e?.response?.data?.error?.message ?? "Не удалось загрузить тесты"));
  }

  useEffect(() => {
    reload();
  }, []);

  async function toggleActive(id: string, current: boolean) {
    try {
      await updateTest(id, { is_active: !current });
      reload();
    } catch (e: unknown) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError((e as any)?.response?.data?.error?.message ?? "Не удалось изменить статус");
    }
  }

  async function remove(id: string) {
    if (!window.confirm("Удалить тест? Это действие необратимо.")) return;
    try {
      await deleteTest(id);
      reload();
    } catch (e: unknown) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError((e as any)?.response?.data?.error?.message ?? "Не удалось удалить тест");
    }
  }

  return (
    <div className="card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2>Тесты</h2>
        <button className="btn" onClick={() => navigate("/manage/tests/new")}>
          + Новый тест
        </button>
      </div>
      {error && <div className="error">{error}</div>}
      {items === null && <p>Загрузка…</p>}
      {items?.length === 0 && <p className="muted">Пока ни одного теста.</p>}
      <table className="table">
        <thead>
          <tr>
            <th>Название</th>
            <th>Вопросов</th>
            <th>Статус</th>
            <th>Создан</th>
            <th>Действия</th>
          </tr>
        </thead>
        <tbody>
          {items?.map((t) => (
            <tr key={t.id}>
              <td>
                <strong>{t.title}</strong>
                {t.description && <div className="muted small">{t.description}</div>}
              </td>
              <td>{t.questions_count}</td>
              <td>{t.is_active ? "активен" : "выключен"}</td>
              <td>{new Date(t.created_at).toLocaleDateString()}</td>
              <td className="actions">
                <Link className="btn secondary" to={`/manage/tests/${t.id}/edit`}>Изменить</Link>
                <Link className="btn secondary" to={`/manage/tests/${t.id}/assign`}>Назначить</Link>
                <button className="btn secondary" onClick={() => toggleActive(t.id, t.is_active)}>
                  {t.is_active ? "Выключить" : "Включить"}
                </button>
                <button className="btn secondary danger" onClick={() => remove(t.id)}>Удалить</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
