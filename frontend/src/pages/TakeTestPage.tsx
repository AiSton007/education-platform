import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  Attempt,
  getTest,
  postAnswers,
  startAttempt,
  submitAttempt,
  Test,
} from "../api";

interface Selection {
  selected_option_ids?: string[];
  free_text?: string;
}

export function TakeTestPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [test, setTest] = useState<Test | null>(null);
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [answers, setAnswers] = useState<Record<string, Selection>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const t = await getTest(id);
        setTest(t);
        const a = await startAttempt(id);
        setAttempt(a);
      } catch (err: unknown) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        setError((err as any)?.response?.data?.error?.message ?? "Cannot start test");
      }
    })();
  }, [id]);

  function selectOption(questionId: string, optionId: string, multiple: boolean) {
    setAnswers((prev) => {
      const current = prev[questionId]?.selected_option_ids ?? [];
      if (!multiple) return { ...prev, [questionId]: { selected_option_ids: [optionId] } };
      const next = current.includes(optionId)
        ? current.filter((id) => id !== optionId)
        : [...current, optionId];
      return { ...prev, [questionId]: { selected_option_ids: next } };
    });
  }

  function setFreeText(questionId: string, text: string) {
    setAnswers((prev) => ({ ...prev, [questionId]: { free_text: text } }));
  }

  async function onSubmit() {
    if (!attempt) return;
    setBusy(true);
    setError(null);
    try {
      const payload = Object.entries(answers).map(([question_id, sel]) => ({
        question_id,
        ...sel,
      }));
      await postAnswers(attempt.id, payload);
      const result = await submitAttempt(attempt.id);
      if (result.report_id) navigate(`/reports/${result.report_id}`);
      else setError("Submitted, no report id returned");
    } catch (err: unknown) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError((err as any)?.response?.data?.error?.message ?? "Submit failed");
    } finally {
      setBusy(false);
    }
  }

  if (!test) return <div className="card">{error ?? "Загрузка…"}</div>;

  return (
    <div className="card">
      <h2>{test.title}</h2>
      {test.description && <p>{test.description}</p>}
      {error && <div className="error">{error}</div>}
      {test.questions.map((q) => (
        <div key={q.id} className="question">
          <div><strong>{q.order + 1}. {q.text}</strong></div>
          {q.type !== "free_text" ? (
            <div className="options">
              {q.options.map((o) => (
                <label key={o.id}>
                  <input
                    type={q.type === "single" ? "radio" : "checkbox"}
                    name={q.id}
                    checked={Boolean(answers[q.id]?.selected_option_ids?.includes(o.id))}
                    onChange={() => selectOption(q.id, o.id, q.type === "multiple")}
                  />
                  {o.text}
                </label>
              ))}
            </div>
          ) : (
            <textarea
              rows={3}
              value={answers[q.id]?.free_text ?? ""}
              onChange={(e) => setFreeText(q.id, e.target.value)}
            />
          )}
        </div>
      ))}
      <button className="btn" onClick={onSubmit} disabled={busy}>
        {busy ? "Отправка…" : "Отправить тест"}
      </button>
    </div>
  );
}
