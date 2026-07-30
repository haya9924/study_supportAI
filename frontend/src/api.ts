// バックエンド API クライアント。
const BASE = "";

async function req<T>(
  path: string,
  opts: RequestInit = {}
): Promise<T> {
  const res = await fetch(BASE + path, {
    headers:
      opts.body instanceof FormData
        ? undefined
        : { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  get: <T>(p: string) => req<T>(p),
  post: <T>(p: string, body?: unknown) =>
    req<T>(p, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  put: <T>(p: string, body?: unknown) =>
    req<T>(p, { method: "PUT", body: body ? JSON.stringify(body) : undefined }),
  del: <T>(p: string) => req<T>(p, { method: "DELETE" }),
  upload: <T>(p: string, form: FormData) =>
    req<T>(p, { method: "POST", body: form }),
};

// --- 型 ---
export interface Course {
  id: number;
  name: string;
  created_at: string;
  material_count: number;
}
export interface Material {
  id: number;
  course_id: number | null;
  kind: string;
  title: string;
  original_filename: string;
  status: string;
  error: string;
  created_at: string;
}
export interface Page {
  id: number;
  page_no: number;
  ocr_text: string;
  status: string;
  error: string;
  has_image: boolean;
}
export interface MaterialDetail extends Material {
  pages: Page[];
}
export interface DeckStats {
  id: number;
  name: string;
  course_id: number | null;
  new_per_day: number; // 0 = デフォルトに従う
  created_at: string;
  total: number;
  due_count: number;
  new_count: number;
  effective_new_per_day: number;
}
export interface Card {
  id: number;
  deck_id: number;
  front: string;
  back: string;
  due: string;
  reps: number;
  is_new: boolean;
  suspended: boolean;
}
export interface ReviewCard {
  card: Card | null;
  intervals: Record<string, string> | null;
  remaining: number;
  new_remaining: number;
}
export interface CardDraft {
  front: string;
  back: string;
}
export interface QuizQuestion {
  id: number;
  order_no: number;
  type: string;
  question: string;
  choices: string[];
}
export interface Quiz {
  id: number;
  course_id: number | null;
  title: string;
  created_at: string;
}
export interface QuizDetail extends Quiz {
  questions: QuizQuestion[];
}
export interface Attempt {
  id: number;
  quiz_id: number;
  status: string;
  answers: Record<string, AnswerRecord>;
  score: number;
}
export interface AnswerRecord {
  response: string;
  correct: boolean | null;
  feedback: string;
  correct_answer: string;
  type: string;
}
export interface ExamFollowup {
  role: string;
  content: string;
}
export interface ExamQuestion {
  problem: string;
  answer: string;
  explanation: string;
  followups: ExamFollowup[];
}
export interface Exam {
  id: number;
  course_id: number | null;
  title: string;
  content_md: string;
  questions: ExamQuestion[] | null;
  messages: { role: string; content: string }[];
  created_at: string;
}
export interface SettingsData {
  api_base_url: string;
  api_key_set: boolean;
  vision_model: string;
  text_model: string;
  new_per_day: string;
  desired_retention: string;
  context_char_budget: string;
  llm_mock: boolean;
}
export interface Dashboard {
  due_today: number;
  new_cards: number;
  reviewed_today: number;
  counts: { materials: number; decks: number; cards: number; quizzes: number };
  recent_materials: { id: number; title: string; status: string; kind: string }[];
}
