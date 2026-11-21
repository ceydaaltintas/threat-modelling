"use client";

import * as React from "react";

type Theme = "light" | "dark";

interface ThemeContextValue {
  theme: Theme;
  toggle: () => void;
}

const ThemeContext = React.createContext<ThemeContextValue | null>(null);
const STORAGE_KEY = "tm.theme";

/** Light is the default; dark is optional, as required by the brief. */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = React.useState<Theme>("light");

  React.useEffect(() => {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (stored === "dark" || stored === "light") setTheme(stored);
    } catch {
      /* private mode: keep the default */
    }
  }, []);

  React.useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      /* ignore */
    }
  }, [theme]);

  const value = React.useMemo<ThemeContextValue>(
    () => ({
      theme,
      toggle: () => setTheme((current) => (current === "dark" ? "light" : "dark")),
    }),
    [theme],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const context = React.useContext(ThemeContext);
  if (!context) throw new Error("useTheme must be used inside <ThemeProvider>");
  return context;
}
