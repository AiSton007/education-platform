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

export function TakeTestPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [test, setTest] = useState<Test | null>(null);
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const t = await getTest(id);
        setTest(t as Test);
        const a = await startAttempt(id);
        setAttempt(a);
      } catch (err: unknown) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        setError((err as any)?.response?.data?.error?.message ?? "Не удалось начать тест");
      }
    })();
  }, [id]);

  function setFreeText(questionId: string, text: string) {
    setAnswers((prev) => ({ ...prev, [questionId]: text }));
  }

  async function onSubmit() {
    if (!attempt || !test) return;
    setBusy(true);
    setError(null);
    try {
      const payload = test.questions.map((q) => ({
        question_id: q.id,
        free_text: answers[q.id] ?? "",
      }));
      await postAnswers(attempt.id, payload);
      const result = await submitAttempt(attempt.id);
      navigate(`/attempts/${result.attempt_id}`);
    } catch (err: unknown) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError((err as any)?.response?.data?.error?.message ?? "Ошибка отправки");
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
          <div className="question-header"><strong>{q.order + 1}. {q.text}</strong></div>
          <textarea
            rows={4}
            placeholder="Ваш ответ свободной формой"
            value={answers[q.id] ?? ""}
            onChange={(e) => setFreeText(q.id, e.target.value)}
          />
        </div>
      ))}
      <button className="btn" onClick={onSubmit} disabled={busy} style={{ marginTop: "1rem" }}>
        {busy ? "Отправка…" : "Завершить тест"}
      </button>
    </div>
  );
}
