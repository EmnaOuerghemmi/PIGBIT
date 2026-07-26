import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';

export interface DepartmentBudget {
  id: string;
  department: string;
  year: number;
  allocated_amount: number;
  notes: string | null;
  spent: number;
  remaining: number;
  utilization: number;      // 0..100
  expenses_count: number;
  headcount: number;
}

export interface BudgetTotals {
  allocated: number;
  spent: number;
  remaining: number;
  utilization: number;      // 0..100
}

export interface BudgetStats {
  year: number;
  totals: BudgetTotals;
  departments: DepartmentBudget[];
}

export interface BudgetExpense {
  id: string;
  label: string;
  category: string;
  amount: number;
  spent_at: string | null;
}

@Injectable({ providedIn: 'root' })
export class BudgetService {
  constructor(private api: ApiService) {}

  getStats(year?: number): Observable<BudgetStats> {
    return this.api.get<BudgetStats>('budget/stats', year ? { year } : undefined);
  }

  getExpenses(budgetId: string): Observable<BudgetExpense[]> {
    return this.api.get<BudgetExpense[]>(`budget/departments/${budgetId}/expenses`);
  }

  addExpense(budgetId: string, expense: { label: string; category: string; amount: number }): Observable<BudgetExpense> {
    return this.api.post<BudgetExpense>(`budget/departments/${budgetId}/expenses`, expense);
  }

  deleteExpense(expenseId: string): Observable<void> {
    return this.api.delete<void>(`budget/expenses/${expenseId}`);
  }

  createDepartment(payload: { department: string; year: number; allocated_amount: number; notes?: string }): Observable<any> {
    return this.api.post('budget/departments', payload);
  }

  updateAllocation(budgetId: string, allocated_amount: number): Observable<any> {
    return this.api.patch(`budget/departments/${budgetId}`, { allocated_amount });
  }

  seedDemo(): Observable<{ created_departments: number }> {
    return this.api.post<{ created_departments: number }>('budget/seed', {});
  }
}
