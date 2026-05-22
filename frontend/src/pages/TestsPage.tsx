import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listTests, TestSummary } from "../api";

export function TestsPage() {
  const [items, setItems] = useState<TestSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listTests()
      .then((r) => setItems(r.items))
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .catch((e: any) => setError(e?.response?.data?.error?.message ?? "Failed to load"));
  }, []);

  return (
    <div className="card">
      <h2>Доступные тесты</h2>
      {error && <div className="error">{error}</div>}
      {items.length === 0 && !error && <p>Тестов пока нет. Попросите менеджера создать их.</p>}
      <ul className="list">
        {items.map((t) => (
          <li key={t.id}>
            <strong>{t.title}</strong>
            {t.description && <div>{t.description}</div>}
            <div style={{ marginTop: ".5rem" }}>
              <Link className="btn" to={`/tests/${t.id}/take`}>Пройти</Link>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
