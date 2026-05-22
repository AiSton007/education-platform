import { Link, Navigate, Route, Routes } from "react-router-dom";
import { LoginPage } from "./pages/LoginPage";
import { RegisterPage } from "./pages/RegisterPage";
import { TestsPage } from "./pages/TestsPage";
import { TakeTestPage } from "./pages/TakeTestPage";
import { ReportPage } from "./pages/ReportPage";

function isAuthed(): boolean {
  return Boolean(localStorage.getItem("access_token"));
}

function logout() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  window.location.href = "/login";
}

export function App() {
  return (
    <>
      <header>
        <h1>Education Platform</h1>
        <nav>
          {isAuthed() ? (
            <>
              <Link to="/tests">Тесты</Link>
              <a href="#" onClick={logout}>Выход</a>
            </>
          ) : (
            <>
              <Link to="/login">Вход</Link>
              <Link to="/register">Регистрация</Link>
            </>
          )}
        </nav>
      </header>
      <main className="container">
        <Routes>
          <Route path="/" element={<Navigate to={isAuthed() ? "/tests" : "/login"} />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/tests" element={<TestsPage />} />
          <Route path="/tests/:id/take" element={<TakeTestPage />} />
          <Route path="/reports/:id" element={<ReportPage />} />
        </Routes>
      </main>
    </>
  );
}
