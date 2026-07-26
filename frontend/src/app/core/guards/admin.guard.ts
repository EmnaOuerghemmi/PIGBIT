import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { filter, map, switchMap, take, of, catchError } from 'rxjs';

/**
 * Admin / RH route guard.
 *
 * 1. Waits for AuthService to finish bootstrapping (filter initialized=true
 *    BEFORE take(1) — see authGuard for the explanation of this pattern).
 * 2. If no token at all → bounce to /login.
 * 3. If we have a token but `currentUser` isn't loaded yet (cold reload),
 *    fetch /users/me first so we can check the role.
 * 4. Only ADMIN / RH_MANAGER / RH_STAFF can enter the backoffice.
 */
export const adminGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  return authService.isInitialized$.pipe(
    filter(initialized => initialized),
    take(1),
    switchMap(() => {
      if (!authService.isAuthenticated()) {
        router.navigate(['/login']);
        return of(false);
      }

      const cached = authService.getCurrentUser();
      const userStream$ = cached
        ? of(cached)
        : authService.loadCurrentUser().pipe(
            catchError(() => of(null)),
          );

      return userStream$.pipe(
        map(user => {
          if (user && (user.role === 'ADMIN' || user.role === 'RH_MANAGER' || user.role === 'RH_STAFF')) {
            return true;
          }
          // Authenticated but not RH → send them to the frontoffice instead
          // of bouncing them to /login (which would be confusing).
          if (user) {
            router.navigate(['/frontoffice/home']);
          } else {
            router.navigate(['/login']);
          }
          return false;
        }),
      );
    }),
  );
};
