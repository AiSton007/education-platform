import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AttemptDetail, getAttempt, getReport, Report } from "../api";

export function AttemptResultPage() {
  const { id = "" } = useParams();
  const [attempt, setAttempt] = useState<AttemptDetail | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setError(null);
        setAttempt(null);
        setReport(null);
        const a = await getAttempt(id);
        setAttempt(a);
        if (a.report_id) {
          const r = await getReport(a.report_id);
          setReport(r);
        }
      } catch (err: unknown) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        setError((err as any)?.response?.data?.error?.message ?? "Не удалось загрузить результат");
      }
    })();
  }, [id]);

  if (error) return <div className="card error">{error}</div>;
  if (!attempt) return <div className="card">Загрузка…</div>;

  const status = attempt.status;
  const items = report?.data.items ?? [];
  const recommendations = report?.data.recommendations ?? attempt.answers.map(() => null);

  return (
    <div className="card">
      <h2>Результат прохождения</h2>
      <div className="meta">
        <div><strong>Статус:</strong> {status}</div>
        <div>
          <strong>Итоговая оценка:</strong>{" "}
          {attempt.score === null ? "пока недоступна" : (
            <span className="pill">{attempt.score.toFixed(1)} / 10</span>
          )}
        </div>
        {status === "failed" && attempt.error && (
          <div className="error" style={{ marginTop: ".75rem" }}>{attempt.error}</div>
        )}
      </div>

      <h3>Ответы по вопросам</h3>
      {items.length > 0 ? (
        <ol className="list">
          {items.map((q) => (
            <li key={q.question_id}>
              <div><strong>{q.text}</strong></div>
              <div className="muted small">Ваш ответ:</div>
              <div>{q.user_answer || <em className="muted">(нет ответа)</em>}</div>
              <div className="muted small" style={{ marginTop: ".25rem" }}>
                Оценка: <strong>{q.score.toFixed(1)}</strong>
                {q.feedback && <> — {q.feedback}</>}
              </div>
            </li>
          ))}
        </ol>
      ) : (
        <ol className="list">
          {attempt.answers.map((a) => (
            <li key={a.id}>
              <div><strong>Вопрос:</strong> {a.question_id}</div>
              <div>{a.free_text || <em className="muted">(нет ответа)</em>}</div>
              <div className="muted small">
                {a.score === null ? "Оценка не выставлена" : `Оценка: ${a.score.toFixed(1)}`}
                {a.feedback && <> — {a.feedback}</>}
              </div>
            </li>
          ))}
        </ol>
      )}

      <h3>Рекомендации к изучению</h3>
      {report?.data.recommendations && report.data.recommendations.length > 0 ? (
        <ul className="list">
          {report.data.recommendations.map((r, i) => (
            <li key={i}>
              <div><strong>{r.topic}</strong></div>
              <div className="muted">{r.reason}</div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">Рекомендаций нет — результаты в пределах ожиданий.</p>
      )}

      <div style={{ marginTop: "1rem", display: "flex", gap: ".5rem" }}>
        <Link className="btn secondary" to="/history">К истории прохождений</Link>
        {attempt.report_id && (
          <Link className="btn secondary" to={`/reports/${attempt.report_id}`}>
            Открыть отчёт
          </Link>
        )}
      </div>
      {recommendations === null && null}
    </div>
  );
}
