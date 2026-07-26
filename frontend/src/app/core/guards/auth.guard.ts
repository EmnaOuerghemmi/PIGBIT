import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { filter, map, take } from 'rxjs/operators';

/**
 * Authenticated route guard.
 *
 * Critical detail: `isInitialized$` is a BehaviorSubject(false), so a plain
 * `take(1)` would immediately receive the initial `false` value before the
 * session-restore HTTP call has even fired. We MUST filter for `true` first
 * so the guard waits for the AuthService to finish bootstrapping.
 *
 * Once initialised, we only need a token in localStorage. Token validity
 * is then enforced by the JWT interceptor (which transparently refreshes
 * expired access tokens), not by this guard.
 */
export const authGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  return authService.isInitialized$.pipe(
    filter(initialized => initialized),
    take(1),
    map(() => {
      if (authService.isAuthenticated()) return true;
      router.navigate(['/login']);
      return false;
    }),
  );
};
