import { FormEvent, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  createTest,
  getTest,
  TestAdmin,
  updateTest,
} from "../api";

interface QuestionDraft {
  order: number;
  text: string;
  correct_answer: string;
  weight: number;
}

interface Props {
  mode: "create" | "edit";
}

const emptyQuestion: QuestionDraft = { order: 0, text: "", correct_answer: "", weight: 1.0 };

export function ManagerTestEditPage({ mode }: Props) {
  const navigate = useNavigate();
  const { id = "" } = useParams();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [isActive, setIsActive] = useState(true);
  const [questions, setQuestions] = useState<QuestionDraft[]>([{ ...emptyQuestion }]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setError(null);
    if (mode === "edit" && id) {
      getTest(id)
        .then((t) => {
          const test = t as TestAdmin;
          setTitle(test.title);
          setDescription(test.description ?? "");
          setIsActive(test.is_active);
          setQuestions(
            test.questions.length > 0
              ? test.questions.map((q) => ({
                  order: q.order,
                  text: q.text,
                  correct_answer: q.correct_answer,
                  weight: q.weight,
                }))
              : [{ ...emptyQuestion }],
          );
        })
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        .catch((e: any) => setError(e?.response?.data?.error?.message ?? "Не удалось загрузить тест"));
    }
  }, [mode, id]);

  function updateQuestion(idx: number, patch: Partial<QuestionDraft>) {
    setQuestions((prev) => prev.map((q, i) => (i === idx ? { ...q, ...patch } : q)));
  }

  function addQuestion() {
    setQuestions((prev) => [...prev, { ...emptyQuestion, order: prev.length }]);
  }

  function removeQuestion(idx: number) {
    setQuestions((prev) => prev.filter((_, i) => i !== idx).map((q, i) => ({ ...q, order: i })));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const payload = {
        title,
        description: description || null,
        questions: questions.map((q, i) => ({
          order: i,
          text: q.text,
          correct_answer: q.correct_answer,
          weight: q.weight,
        })),
      };
      if (mode === "create") {
        await createTest(payload);
      } else {
        await updateTest(id, { ...payload, is_active: isActive });
      }
      navigate("/manage/tests");
    } catch (err: unknown) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError((err as any)?.response?.data?.error?.message ?? "Ошибка сохранения");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <h2>{mode === "create" ? "Новый тест" : "Редактирование теста"}</h2>
      {error && <div className="error">{error}</div>}
      <form onSubmit={onSubmit}>
        <label>Название</label>
        <input required value={title} onChange={(e) => setTitle(e.target.value)} />
        <label>Описание</label>
        <textarea rows={2} value={description} onChange={(e) => setDescription(e.target.value)} />
        {mode === "edit" && (
          <label className="checkbox">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
            />
            <span>Тест активен (виден сотрудникам)</span>
          </label>
        )}

        <h3 style={{ marginTop: "1.5rem" }}>Вопросы</h3>
        {questions.map((q, idx) => (
          <div key={idx} className="question editor">
            <div className="question-header">
              <strong>Вопрос {idx + 1}</strong>
              {questions.length > 1 && (
                <button
                  type="button"
                  className="btn secondary danger small"
                  onClick={() => removeQuestion(idx)}
                >
                  Удалить
                </button>
              )}
            </div>
            <label>Текст вопроса</label>
            <textarea
              required
              rows={2}
              value={q.text}
              onChange={(e) => updateQuestion(idx, { text: e.target.value })}
            />
            <label>Правильный ответ (его увидит только GigaChat)</label>
            <textarea
              required
              rows={2}
              value={q.correct_answer}
              onChange={(e) => updateQuestion(idx, { correct_answer: e.target.value })}
            />
          </div>
        ))}
        <button type="button" className="btn secondary" onClick={addQuestion}>
          + Добавить вопрос
        </button>

        <div style={{ marginTop: "1rem" }}>
          <button className="btn" type="submit" disabled={busy}>
            {busy ? "Сохранение…" : "Сохранить"}
          </button>
        </div>
      </form>
    </div>
  );
}
