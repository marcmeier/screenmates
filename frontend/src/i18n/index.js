import { createI18n } from "vue-i18n";
import de from "./de";
import en from "./en";

// The app speaks German and English. Your choice is kept with your profile (all devices);
// before you have a name, this device's last choice or the browser's language decides.
// Film data (titles, plots, genres) comes from TMDB in the server's TMDB_LANGUAGE.
export const SPRACHEN = { de: "Deutsch", en: "English" };
const KEY = "screenmates.sprache";

function erste() {
  try {
    const gemerkt = localStorage.getItem(KEY);
    if (SPRACHEN[gemerkt]) return gemerkt;
  } catch {
    /* private mode */
  }
  const browser = navigator.languages?.length
    ? navigator.languages
    : [navigator.language || "de"];
  return browser.some((l) => l?.toLowerCase().startsWith("de")) ? "de" : "en";
}

export const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: erste(),
  fallbackLocale: "de",
  messages: { de, en },
});
document.documentElement.lang = i18n.global.locale.value;

export const t = (...args) => i18n.global.t(...args);
export const sprache = () => i18n.global.locale.value;
/** For Intl formatters: dates like "Freitag, 9. Oktober" / "Friday 9 October". */
export const locale = () => (sprache() === "en" ? "en-GB" : "de-DE");

export function spracheSetzen(s) {
  if (!SPRACHEN[s] || s === sprache()) return;
  i18n.global.locale.value = s;
  document.documentElement.lang = s;
  try {
    localStorage.setItem(KEY, s);
  } catch {
    /* private mode */
  }
}
