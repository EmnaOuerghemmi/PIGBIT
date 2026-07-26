import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';

export interface CareerStats {
  probation: number;
  promotions_planned: number;
  in_progress: number;
  retirements_planned: number;
  total: number;
}

export interface CareerPlan {
  id: string;
  user_id: string;
  current_position: string | null;
  target_position: string | null;
  status: string;
  progress: number;
  skills_to_develop: string | null;
  notes: string | null;
  target_date: string | null;
  created_at: string;
  updated_at: string | null;
  employee_name: string | null;
}

@Injectable({ providedIn: 'root' })
export class CareerService {
  constructor(private api: ApiService) {}

  getStats(): Observable<CareerStats> {
    return this.api.get<CareerStats>('career/stats');
  }

  getPlans(statusFilter?: string): Observable<CareerPlan[]> {
    const params: Record<string, string> = {};
    if (statusFilter) params['status_filter'] = statusFilter;
    return this.api.get<CareerPlan[]>('career/plans', params);
  }

  createPlan(data: Partial<CareerPlan> & { user_id: string }): Observable<CareerPlan> {
    return this.api.post<CareerPlan>('career/plans', data);
  }

  updatePlan(planId: string, data: Partial<CareerPlan>): Observable<CareerPlan> {
    return this.api.patch<CareerPlan>(`career/plans/${planId}`, data);
  }

  deletePlan(planId: string): Observable<void> {
    return this.api.delete<void>(`career/plans/${planId}`);
  }
}
