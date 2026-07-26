import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { User, UserCreate, UserUpdate, UserAdminUpdate, PaginatedUsers } from '../models/user.model';

export interface UserListParams {
  page?: number;
  size?: number;
  role?: string;
  ministry?: string;
  is_active?: boolean;
  search?: string;
}

export interface AuditLog {
  id: string;
  user_id: string | null;
  action: string;
  resource: string | null;
  resource_id: string | null;
  details: Record<string, any> | null;
  ip_address: string | null;
  created_at: string;
}

export interface PaginatedAuditLogs {
  total: number;
  page: number;
  size: number;
  items: AuditLog[];
}

@Injectable({
  providedIn: 'root'
})
export class UserService {
  constructor(private api: ApiService) {}

  getMe(): Observable<User> {
    return this.api.get<User>('users/me');
  }

  updateMe(data: UserUpdate): Observable<User> {
    return this.api.patch<User>('users/me', data);
  }

  /** Self-service account deletion (profile Danger zone). */
  deleteMe(): Observable<void> {
    return this.api.delete<void>('users/me');
  }

  /** Change own password. */
  changePassword(currentPassword: string, newPassword: string): Observable<any> {
    return this.api.post('auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
  }

  listUsers(params: UserListParams = {}): Observable<PaginatedUsers> {
    const queryParams: Record<string, string | number | boolean> = {};
    if (params.page !== undefined) queryParams['page'] = params.page;
    if (params.size !== undefined) queryParams['size'] = params.size;
    if (params.role) queryParams['role'] = params.role;
    if (params.ministry) queryParams['ministry'] = params.ministry;
    if (params.is_active !== undefined) queryParams['is_active'] = params.is_active;
    if (params.search) queryParams['search'] = params.search;
    return this.api.get<PaginatedUsers>('users', queryParams);
  }

  createUser(data: UserCreate): Observable<User> {
    return this.api.post<User>('users', data);
  }

  getUser(userId: string): Observable<User> {
    return this.api.get<User>(`users/${userId}`);
  }

  updateUser(userId: string, data: UserAdminUpdate): Observable<User> {
    return this.api.patch<User>(`users/${userId}`, data);
  }

  deleteUser(userId: string): Observable<void> {
    return this.api.delete<void>(`users/${userId}`);
  }

  getAuditLogs(userId?: string, page = 1, size = 50): Observable<PaginatedAuditLogs> {
    const params: Record<string, string | number> = { page, size };
    if (userId) params['user_id'] = userId;
    return this.api.get<PaginatedAuditLogs>('users/audit-logs', params);
  }

  getMyAuditLogs(page = 1, size = 20): Observable<PaginatedAuditLogs> {
    return this.api.get<PaginatedAuditLogs>('users/me/audit-logs', { page, size });
  }
}
