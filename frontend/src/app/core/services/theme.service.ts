import { Injectable, signal } from '@angular/core';

export type Theme = 'light' | 'dark';

const STORAGE_KEY = 'piqbit-theme';

/**
 * Thème clair / sombre du frontoffice.
 *
 * Le thème effectif est porté par l'attribut `data-theme` sur <html> ; toute la
 * feuille de styles s'y accroche. Le choix de l'utilisateur est persisté, et à
 * défaut on suit la préférence du système — tant que l'utilisateur n'a rien
 * choisi explicitement, un changement de thème de l'OS est répercuté à chaud.
 */
@Injectable({ providedIn: 'root' })
export class ThemeService {
  /** Thème appliqué actuellement (lisible en template via `theme()`). */
  readonly theme = signal<Theme>('dark');

  private media?: MediaQueryList;

  constructor() {
    this.media = window.matchMedia?.('(prefers-color-scheme: light)');
    this.apply(this.resolveInitial(), false);

    // Suit l'OS uniquement si l'utilisateur n'a pas fait de choix explicite.
    this.media?.addEventListener?.('change', (e) => {
      if (this.stored() === null) this.apply(e.matches ? 'light' : 'dark', false);
    });
  }

  toggle(): void {
    this.apply(this.theme() === 'dark' ? 'light' : 'dark', true);
  }

  set(theme: Theme): void {
    this.apply(theme, true);
  }

  private apply(theme: Theme, persist: boolean): void {
    this.theme.set(theme);
    document.documentElement.setAttribute('data-theme', theme);
    // Aligne les UI natives (barres de défilement, champs de formulaire).
    document.documentElement.style.colorScheme = theme;
    if (persist) {
      try { localStorage.setItem(STORAGE_KEY, theme); } catch { /* stockage indisponible */ }
    }
  }

  private resolveInitial(): Theme {
    const saved = this.stored();
    if (saved) return saved;
    return this.media?.matches ? 'light' : 'dark';
  }

  private stored(): Theme | null {
    try {
      const v = localStorage.getItem(STORAGE_KEY);
      return v === 'light' || v === 'dark' ? v : null;
    } catch {
      return null;
    }
  }
}
