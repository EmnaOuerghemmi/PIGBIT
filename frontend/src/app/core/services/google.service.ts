import { Injectable } from '@angular/core';
import { Observable, Subject } from 'rxjs';

declare global {
  interface Window {
    google: {
      accounts: {
        id: {
          initialize: (config: any) => void;
          renderButton: (element: HTMLElement, options: any) => void;
          getCredential?: () => string;
          cancel?: () => void;
        };
      };
    };
  }
}

@Injectable({
  providedIn: 'root'
})
export class GoogleService {
  private googleClientId = ''; // Will be set from environment
  private credentialResponse$ = new Subject<string>();
  public credentialResponse = this.credentialResponse$.asObservable();
  private isInitialized = false;
  private renderRetries = 0;

  constructor() {}

  private initializeGoogle(): void {
    if (typeof window !== 'undefined' && window.google && !this.isInitialized && this.googleClientId) {
      window.google.accounts.id.initialize({
        client_id: this.googleClientId,
        callback: (response: any) => this.handleCredentialResponse(response),
        auto_select: false,
        cancel_on_tap_outside: true,
      });
      this.isInitialized = true;
    }
  }

  renderButton(elementId: string, opts: { iconOnly?: boolean } = {}): void {
    if (typeof window === 'undefined') return;

    const element = document.getElementById(elementId);
    if (!element) return;

    if (!window.google || !this.googleClientId) {
      if (this.renderRetries < 20) {
        this.renderRetries++;
        setTimeout(() => this.renderButton(elementId, opts), 150);
      }
      return;
    }

    this.initializeGoogle();

    if (this.isInitialized) {
      element.innerHTML = '';
      if (opts.iconOnly) {
        // Circular, icon-only Google "G" — matches the reference design.
        window.google.accounts.id.renderButton(element, {
          type: 'icon',
          shape: 'circle',
          theme: 'outline',
          size: 'large',
        });
      } else {
        window.google.accounts.id.renderButton(element, {
          type: 'standard',
          theme: 'filled_black',
          size: 'medium',
          text: 'signin_with',
          locale: 'fr',
          logo_alignment: 'left',
          width: Math.min(element.clientWidth || 320, 360),
        });
      }
    }
  }

  private handleCredentialResponse(response: any): void {
    if (response.credential) {
      this.credentialResponse$.next(response.credential);
    }
  }

  getIdToken(): Promise<string> {
    return new Promise((resolve, reject) => {
      if (typeof window !== 'undefined' && window.google) {
        // This will trigger the credential callback
        const credential = window.google.accounts.id.getCredential?.();
        if (credential) {
          resolve(credential);
        } else {
          reject(new Error('No credential available'));
        }
      } else {
        reject(new Error('Google not initialized'));
      }
    });
  }

  setClientId(clientId: string): void {
    if (this.googleClientId !== clientId) {
      this.googleClientId = clientId;
      this.isInitialized = false;
      // Initialize Google with the new Client ID
      this.initializeGoogle();
    }
  }
}
