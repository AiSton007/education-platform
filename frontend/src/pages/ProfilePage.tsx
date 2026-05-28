import { useEffect, useState } from "react";
import { fetchMe, Me } from "../api";

export function ProfilePage() {
  const [profile, setProfile] = useState<Me | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    fetchMe()
      .then(setProfile)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .catch((e: any) => setError(e?.response?.data?.error?.message ?? "Не удалось загрузить профиль"));
  }, []);

  if (error) return <div className="card error">{error}</div>;
  if (!profile) return <div className="card">Загрузка профиля…</div>;

  return (
    <div className="card">
      <h2>Профиль пользователя</h2>
      <div className="meta">
        <div><strong>Email:</strong> {profile.email}</div>
        <div><strong>Имя:</strong> {profile.full_name}</div>
        <div><strong>Подразделение:</strong> {profile.department ?? "—"}</div>
        <div><strong>Должность:</strong> {profile.position ?? "—"}</div>
        <div><strong>Роль:</strong> {profile.role}</div>
        <div><strong>Статус:</strong> {profile.is_active ? "активен" : "деактивирован"}</div>
      </div>
    </div>
  );
}
