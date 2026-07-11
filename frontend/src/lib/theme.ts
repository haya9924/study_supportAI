// ライト / ダークテーマの管理。
// 明示選択は localStorage に保存し、未選択のときは OS 設定に追従する。
import { useEffect, useState } from "react";

const KEY = "theme";

function systemPrefersDark(): boolean {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function storedTheme(): "light" | "dark" | null {
  const v = localStorage.getItem(KEY);
  return v === "light" || v === "dark" ? v : null;
}

function currentIsDark(): boolean {
  const s = storedTheme();
  return s ? s === "dark" : systemPrefersDark();
}

function applyTheme(isDark: boolean): void {
  document.documentElement.classList.toggle("dark", isDark);
}

/** [isDark, toggle] を返すフック。切替時に localStorage へ保存する。 */
export function useTheme(): [boolean, () => void] {
  const [isDark, setIsDark] = useState<boolean>(() => currentIsDark());

  // 未選択のときは OS のテーマ変更に追従
  useEffect(() => {
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const onChange = () => {
      if (!storedTheme()) setIsDark(mq.matches);
    };
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  useEffect(() => {
    applyTheme(isDark);
  }, [isDark]);

  const toggle = () => {
    setIsDark((prev) => {
      const next = !prev;
      localStorage.setItem(KEY, next ? "dark" : "light");
      return next;
    });
  };

  return [isDark, toggle];
}
