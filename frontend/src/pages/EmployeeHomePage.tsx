import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  AttemptHistoryItem,
  AvailableTest,
  myAssignments,
  myHistory,
} from "../api";

interface Props {
  tab?: "available" | "history";
}

export function EmployeeHomePage({ tab = "available" }: Props) {
  const [available, setAvailable] = useState<AvailableTest[] | null>(null);
  const [history, setHistory] = useState<AttemptHistoryItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    Promise.all([myAssignments(), myHistory()])
      .then(([a, h]) => {
        setAvailable(a.items);
        setHistory(h.items);
      })
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .catch((e: any) => setError(e?.response?.data?.error?.message ?? "Не удалось загрузить данные"));
  }, []);

  return (
    <>
      {error && <div className="error">{error}</div>}

      {tab === "available" && (
        <div className="card">
          <h2>Тесты, которые нужно пройти</h2>
          {available === null && <p>Загрузка…</p>}
          {available?.length === 0 && (
            <p className="muted">Свободных тестов нет — ничего проходить не нужно.</p>
          )}
          <ul className="list">
            {available?.map((t) => (
              <li key={t.assignment_id}>
                <div>
                  <strong>{t.title}</strong>
                  {t.description && <div className="muted">{t.description}</div>}
                  <div className="muted small">
                    Вопросов: {t.questions_count}
                    {t.due_date && ` · Срок: ${new Date(t.due_date).toLocaleString()}`}
                  </div>
                </div>
                <div style={{ marginTop: ".5rem" }}>
                  <Link className="btn" to={`/tests/${t.test_id}/take`}>Пройти</Link>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="card">
        <h2>{tab === "history" ? "История прохождений" : "Недавние результаты"}</h2>
        {history === null && <p>Загрузка…</p>}
        {history?.length === 0 && <p className="muted">Вы ещё не проходили тестов.</p>}
        <table className="table">
          <thead>
            <tr>
              <th>Тест</th>
              <th>Статус</th>
              <th>Оценка</th>
              <th>Завершён</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {history?.map((h) => (
              <tr key={h.attempt_id}>
                <td>{h.test_title}</td>
                <td>{h.status}</td>
                <td>{h.score === null ? "—" : h.score.toFixed(1)}</td>
                <td>{h.completed_at ? new Date(h.completed_at).toLocaleString() : "—"}</td>
                <td>
                  {h.report_id ? (
                    <Link className="btn secondary" to={`/reports/${h.report_id}`}>Отчёт</Link>
                  ) : (
                    <Link className="btn secondary" to={`/attempts/${h.attempt_id}`}>Подробнее</Link>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
