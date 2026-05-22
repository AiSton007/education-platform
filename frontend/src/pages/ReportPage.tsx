import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getReport, Report } from "../api";

export function ReportPage() {
  const { id = "" } = useParams();
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getReport(id)
      .then(setReport)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .catch((e: any) => setError(e?.response?.data?.error?.message ?? "Cannot load report"));
  }, [id]);

  if (error) return <div className="card error">{error}</div>;
  if (!report) return <div className="card">Загрузка отчёта…</div>;

  return (
    <div className="card">
      <h2>Отчёт</h2>
      <div><strong>Оценка:</strong> {report.score.toFixed(1)} / 100</div>
      <h3>Сильные стороны</h3>
      <ul>{report.data.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
      <h3>Слабые стороны</h3>
      <ul>{report.data.weaknesses.map((w, i) => <li key={i}>{w}</li>)}</ul>
      <h3>Что изучить</h3>
      <ul>
        {report.recommendations.map((r) => (
          <li key={r.id}>
            <strong>{r.topic}</strong> — {r.reason}
            {r.resource_url && <> (<a href={r.resource_url} target="_blank" rel="noreferrer">материалы</a>)</>}
          </li>
        ))}
      </ul>
    </div>
  );
}
