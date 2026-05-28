import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  AttemptDetail,
  downloadReportPdf,
  getAttempt,
  getReport,
  getUser,
  Profile,
  Report,
} from "../api";

export function ManagerAttemptDetailPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [attempt, setAttempt] = useState<AttemptDetail | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [participant, setParticipant] = useState<Profile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        setError(null);
        setAttempt(null);
        setReport(null);
        setParticipant(null);
        const a = await getAttempt(id);
        setAttempt(a);
        const tasks: Promise<unknown>[] = [];
        tasks.push(
          getUser(a.user_id).then(setParticipant).catch(() => undefined),
        );
        if (a.report_id) {
          tasks.push(getReport(a.report_id).then(setReport).catch(() => undefined));
        }
        await Promise.all(tasks);
      } catch (e: unknown) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        setError((e as any)?.response?.data?.error?.message ?? "Не удалось загрузить попытку");
      }
    })();
  }, [id]);

  async function onDownload() {
    if (!attempt?.report_id) return;
    setDownloading(true);
    try {
      const blob = await downloadReportPdf(attempt.report_id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report-${attempt.report_id}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e: unknown) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError((e as any)?.response?.data?.error?.message ?? "Не удалось скачать PDF");
    } finally {
      setDownloading(false);
    }
  }

  if (error) return <div className="card error">{error}</div>;
  if (!attempt) return <div className="card">Загрузка…</div>;

  const items = report?.data.items ?? [];

  return (
    <div className="card">
      <button className="btn secondary small" onClick={() => navigate("/manage/attempts")}>
        ← Назад
      </button>
      <h2>Прохождение теста</h2>
      <div className="meta">
        {participant && (
          <div><strong>Сотрудник:</strong> {participant.full_name} ({participant.email})</div>
        )}
        <div><strong>Статус:</strong> {attempt.status}</div>
        <div>
          <strong>Итоговая оценка:</strong>{" "}
          {attempt.score === null ? "—" : (
            <span className="pill">{attempt.score.toFixed(1)} / 1.0</span>
          )}
        </div>
      </div>

      {attempt.report_id && (
        <div style={{ margin: "1rem 0", display: "flex", gap: ".5rem" }}>
          <button className="btn" onClick={onDownload} disabled={downloading}>
            {downloading ? "Готовим PDF…" : "Скачать PDF отчёт"}
          </button>
          <Link className="btn secondary" to={`/reports/${attempt.report_id}`}>
            Открыть отчёт
          </Link>
        </div>
      )}

      <h3>Ответы по вопросам</h3>
      {items.length > 0 ? (
        <ol className="list">
          {items.map((q) => (
            <li key={q.question_id}>
              <div><strong>{q.text}</strong></div>
              <div className="muted small">Правильный ответ:</div>
              <div>{q.correct_answer}</div>
              <div className="muted small">Ответ сотрудника:</div>
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
              <div>{a.free_text || <em className="muted">(нет ответа)</em>}</div>
              <div className="muted small">
                {a.score === null ? "Оценка не выставлена" : `Оценка: ${a.score.toFixed(1)}`}
                {a.feedback && <> — {a.feedback}</>}
              </div>
            </li>
          ))}
        </ol>
      )}

      {report?.data.recommendations && (
        <>
          <h3>Рекомендации</h3>
          <ul className="list">
            {report.data.recommendations.map((r, i) => (
              <li key={i}>
                <strong>{r.topic}</strong>
                <div className="muted">{r.reason}</div>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
