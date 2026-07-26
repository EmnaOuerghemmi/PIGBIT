import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';

export interface ForgotPasswordRequest {
  email: string;
}

export interface ResetPasswordRequest {
  token: string;
  new_password: string;
}

export interface VerifyEmailRequest {
  token: string;
}

@Injectable({
  providedIn: 'root'
})
export class PasswordService {
  constructor(private api: ApiService) {}

  forgotPassword(email: string): Observable<any> {
    return this.api.post('auth/forgot-password', { email });
  }

  resetPassword(token: string, newPassword: string): Observable<any> {
    return this.api.post('auth/reset-password', { token, new_password: newPassword });
  }

  verifyEmail(token: string): Observable<any> {
    return this.api.post('auth/verify-email', { token });
  }
}
