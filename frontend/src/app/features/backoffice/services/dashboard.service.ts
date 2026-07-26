import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class DashboardService {
  private apiUrl = `${environment.apiUrl}/dashboard`;

  constructor(private http: HttpClient) {}

  /**
   * Get dashboard statistics
   * Returns: total_jobs, total_applications, total_hires, and if superadmin: active_users, new_users
   */
  getDashboardStats(): Observable<any> {
    return this.http.get(`${this.apiUrl}/stats`);
  }

  /**
   * Get recent applications (last 4)
   */
  getRecentApplications(limit: number = 4): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/recent-applications?limit=${limit}`);
  }

  /**
   * Get open positions (last 3)
   */
  getOpenPositions(limit: number = 3): Observable<any[]> {
    return this.http.get<any[]>(`${this.apiUrl}/open-positions?limit=${limit}`);
  }
}
