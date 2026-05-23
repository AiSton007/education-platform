import { useEffect, useState } from "react";
import {
  adminResetPassword,
  deactivateUser,
  listUsers,
  patchUser,
  Profile,
  Role,
} from "../api";

export function AdminUsersPage() {
  const [users, setUsers] = useState<Profile[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  function reload() {
    listUsers()
      .then((r) => setUsers(r.items))
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      .catch((e: any) => setError(e?.response?.data?.error?.message ?? "Не удалось загрузить пользователей"));
  }

  useEffect(() => {
    reload();
  }, []);

  async function changeRole(user_id: string, role: Role) {
    try {
      await patchUser(user_id, { role });
      reload();
    } catch (e: unknown) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError((e as any)?.response?.data?.error?.message ?? "Не удалось изменить роль");
    }
  }

  async function toggleActive(u: Profile) {
    try {
      if (u.is_active) {
        await deactivateUser(u.user_id);
      } else {
        await patchUser(u.user_id, { is_active: true });
      }
      reload();
    } catch (e: unknown) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError((e as any)?.response?.data?.error?.message ?? "Не удалось изменить статус");
    }
  }

  async function resetPassword(u: Profile) {
    const pwd = window.prompt(
      `Введите новый пароль для ${u.email} (минимум 8 символов):`,
    );
    if (!pwd) return;
    if (pwd.length < 8) {
      alert("Пароль должен быть не короче 8 символов");
      return;
    }
    try {
      await adminResetPassword(u.user_id, pwd);
      alert("Пароль сброшен. Сообщите его пользователю безопасным способом.");
    } catch (e: unknown) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      setError((e as any)?.response?.data?.error?.message ?? "Не удалось сбросить пароль");
    }
  }

  return (
    <div className="card">
      <h2>Управление пользователями</h2>
      {error && <div className="error">{error}</div>}
      {users === null && <p>Загрузка…</p>}
      <table className="table">
        <thead>
          <tr>
            <th>Сотрудник</th>
            <th>Email</th>
            <th>Подразделение</th>
            <th>Должность</th>
            <th>Роль</th>
            <th>Статус</th>
            <th>Действия</th>
          </tr>
        </thead>
        <tbody>
          {users?.map((u) => (
            <tr key={u.user_id} className={u.is_active ? "" : "inactive"}>
              <td>{u.full_name}</td>
              <td>{u.email}</td>
              <td>{u.department ?? "—"}</td>
              <td>{u.position ?? "—"}</td>
              <td>
                <select
                  value={u.role}
                  onChange={(e) => changeRole(u.user_id, e.target.value as Role)}
                >
                  <option value="employee">employee</option>
                  <option value="manager">manager</option>
                  <option value="admin">admin</option>
                </select>
              </td>
              <td>{u.is_active ? "активен" : "выключен"}</td>
              <td className="actions">
                <button className="btn secondary" onClick={() => toggleActive(u)}>
                  {u.is_active ? "Деактивировать" : "Активировать"}
                </button>
                <button className="btn secondary" onClick={() => resetPassword(u)}>
                  Сбросить пароль
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
