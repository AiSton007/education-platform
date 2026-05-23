import { ReactNode } from "react";
import { Link, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { getStoredRole, isAuthenticated, Role } from "./api";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { EmployeeHomePage } from "./pages/EmployeeHomePage";
import { TakeTestPage } from "./pages/TakeTestPage";
import { ReportPage } from "./pages/ReportPage";
import { ManagerTestsPage } from "./pages/ManagerTestsPage";
import { ManagerTestEditPage } from "./pages/ManagerTestEditPage";
import { ManagerAttemptsPage } from "./pages/ManagerAttemptsPage";
import { ManagerAttemptDetailPage } from "./pages/ManagerAttemptDetailPage";
import { ManagerAssignTestPage } from "./pages/ManagerAssignTestPage";
import { AdminUsersPage } from "./pages/AdminUsersPage";
import { AttemptResultPage } from "./pages/AttemptResultPage";

function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  window.location.href = "/login";
}

function homePathForRole(role: Role | null): string {
  if (role === "manager" || role === "admin") return "/manage/tests";
  if (role === "employee") return "/home";
  return "/login";
}

interface GuardProps {
  children: ReactNode;
  roles?: Role[];
}

function Guard({ children, roles }: GuardProps) {
  const location = useLocation();
  if (!isAuthenticated()) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }
  const role = getStoredRole();
  if (roles && (!role || !roles.includes(role))) {
    return <Navigate to={homePathForRole(role)} replace />;
  }
  return <>{children}</>;
}

function Nav() {
  const role = getStoredRole();
  const authed = isAuthenticated();
  return (
    <nav>
      {authed ? (
        <>
          {role === "employee" && (
            <>
              <Link to="/home">Главная</Link>
              <Link to="/history">История</Link>
            </>
          )}
          {(role === "manager" || role === "admin") && (
            <>
              <Link to="/manage/tests">Тесты</Link>
              <Link to="/manage/attempts">Прохождения</Link>
            </>
          )}
          {role === "admin" && <Link to="/admin/users">Пользователи</Link>}
          <a href="#" onClick={logout}>Выход</a>
        </>
      ) : (
        <>
          <Link to="/login">Вход</Link>
          <Link to="/register">Регистрация</Link>
        </>
      )}
    </nav>
  );
}

export function App() {
  return (
    <>
      <header>
        <h1>Education Platform</h1>
        <Nav />
      </header>
      <main className="container">
        <Routes>
          <Route
            path="/"
            element={<Navigate to={isAuthenticated() ? homePathForRole(getStoredRole()) : "/login"} />}
          />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          <Route
            path="/home"
            element={
              <Guard roles={["employee"]}>
                <EmployeeHomePage />
              </Guard>
            }
          />
          <Route
            path="/history"
            element={
              <Guard roles={["employee"]}>
                <EmployeeHomePage tab="history" />
              </Guard>
            }
          />
          <Route
            path="/tests/:id/take"
            element={
              <Guard roles={["employee", "manager", "admin"]}>
                <TakeTestPage />
              </Guard>
            }
          />
          <Route
            path="/attempts/:id"
            element={
              <Guard roles={["employee", "manager", "admin"]}>
                <AttemptResultPage />
              </Guard>
            }
          />
          <Route
            path="/reports/:id"
            element={
              <Guard roles={["employee", "manager", "admin"]}>
                <ReportPage />
              </Guard>
            }
          />

          <Route
            path="/manage/tests"
            element={
              <Guard roles={["manager", "admin"]}>
                <ManagerTestsPage />
              </Guard>
            }
          />
          <Route
            path="/manage/tests/new"
            element={
              <Guard roles={["manager", "admin"]}>
                <ManagerTestEditPage mode="create" />
              </Guard>
            }
          />
          <Route
            path="/manage/tests/:id/edit"
            element={
              <Guard roles={["manager", "admin"]}>
                <ManagerTestEditPage mode="edit" />
              </Guard>
            }
          />
          <Route
            path="/manage/tests/:id/assign"
            element={
              <Guard roles={["manager", "admin"]}>
                <ManagerAssignTestPage />
              </Guard>
            }
          />
          <Route
            path="/manage/attempts"
            element={
              <Guard roles={["manager", "admin"]}>
                <ManagerAttemptsPage />
              </Guard>
            }
          />
          <Route
            path="/manage/attempts/:id"
            element={
              <Guard roles={["manager", "admin"]}>
                <ManagerAttemptDetailPage />
              </Guard>
            }
          />

          <Route
            path="/admin/users"
            element={
              <Guard roles={["admin"]}>
                <AdminUsersPage />
              </Guard>
            }
          />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </>
  );
}
