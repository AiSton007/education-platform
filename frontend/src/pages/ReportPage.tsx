import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  downloadReportPdf,
  getReport,
  getStoredRole,
  Report,
} from "../api";

export function ReportPage() {
  const { id = "" } = useParams();
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    setError(null);
    setReport(null);
    getReport(id)
      .then(setReport)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .catch((e: any) => setError(e?.response?.data?.error?.message ?? "Cannot load report"));
  }, [id]);

  const role = getStoredRole();
  const canDownloadPdf = role === "manager" || role === "admin";

  async function onDownload() {
    if (!report) return;
    setDownloading(true);
    try {
      const blob = await downloadReportPdf(report.id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report-${report.id}.pdf`;
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
  if (!report) return <div className="card">Загрузка отчёта…</div>;

  const items = report.data.items ?? [];
  const recos = report.data.recommendations ?? report.recommendations;
  const participant = report.data.participant;
  const test = report.data.test;

  return (
    <div className="card">
      <h2>Отчёт</h2>
      <div className="meta">
        {test?.title && <div><strong>Тест:</strong> {test.title}</div>}
        {participant?.full_name && (
          <div>
            <strong>Участник:</strong> {participant.full_name}
            {participant.email && ` (${participant.email})`}
          </div>
        )}
        <div>
          <strong>Итоговая оценка:</strong>{" "}
          <span className="pill">{report.score.toFixed(1)} / 10</span>
        </div>
      </div>

      {canDownloadPdf && (
        <button className="btn" onClick={onDownload} disabled={downloading} style={{ margin: ".75rem 0" }}>
          {downloading ? "Готовим PDF…" : "Скачать PDF"}
        </button>
      )}

      <h3>Вопросы</h3>
      {items.length === 0 && <p className="muted">Нет данных по вопросам.</p>}
      <ol className="list">
        {items.map((q) => (
          <li key={q.question_id}>
            <div><strong>{q.text}</strong></div>
            <div className="muted small">Правильный ответ:</div>
            <div>{q.correct_answer}</div>
            <div className="muted small">Ответ пользователя:</div>
            <div>{q.user_answer || <em className="muted">(нет ответа)</em>}</div>
            <div className="muted small" style={{ marginTop: ".25rem" }}>
              Оценка: <strong>{q.score.toFixed(1)}</strong>
              {q.feedback && <> — {q.feedback}</>}
            </div>
          </li>
        ))}
      </ol>

      <h3>Рекомендации к изучению</h3>
      <ul className="list">
        {recos.map((r, i) => (
          <li key={i}>
            <strong>{r.topic}</strong>
            <div className="muted">{r.reason}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}
