import { NavLink, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Materials from "./pages/Materials";
import CourseView from "./pages/CourseView";
import MaterialDetail from "./pages/MaterialDetail";
import Decks from "./pages/Decks";
import DeckDetail from "./pages/DeckDetail";
import Review from "./pages/Review";
import Quizzes from "./pages/Quizzes";
import QuizTake from "./pages/QuizTake";
import Exams from "./pages/Exams";
import ExamDetail from "./pages/ExamDetail";
import Settings from "./pages/Settings";

const nav = [
  { to: "/", label: "ホーム", icon: "🏠", end: true },
  { to: "/materials", label: "教材", icon: "📄" },
  { to: "/decks", label: "フラッシュカード", icon: "🃏" },
  { to: "/quizzes", label: "クイズ", icon: "✅" },
  { to: "/exams", label: "予想問題", icon: "📝" },
  { to: "/settings", label: "設定", icon: "⚙️" },
];

export default function App() {
  return (
    <div className="min-h-screen flex">
      <aside className="w-56 bg-white border-r border-slate-200 flex-shrink-0 no-print">
        <div className="p-5 border-b border-slate-100">
          <div className="font-bold text-lg text-indigo-700">study_supportAI</div>
          <div className="text-xs text-slate-400">学習支援</div>
        </div>
        <nav className="p-3 space-y-1">
          {nav.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition ${
                  isActive
                    ? "bg-indigo-50 text-indigo-700"
                    : "text-slate-600 hover:bg-slate-100"
                }`
              }
            >
              <span>{n.icon}</span>
              {n.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto p-6">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/materials" element={<Materials />} />
            <Route path="/materials/course/:cid" element={<CourseView />} />
            <Route path="/materials/:id" element={<MaterialDetail />} />
            <Route path="/decks" element={<Decks />} />
            <Route path="/decks/:id" element={<DeckDetail />} />
            <Route path="/decks/:id/review" element={<Review />} />
            <Route path="/quizzes" element={<Quizzes />} />
            <Route path="/quizzes/:id" element={<QuizTake />} />
            <Route path="/exams" element={<Exams />} />
            <Route path="/exams/:id" element={<ExamDetail />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}
