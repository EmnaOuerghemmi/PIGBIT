import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  BudgetService, BudgetStats, DepartmentBudget, BudgetExpense,
} from '../../../core/services/budget.service';

@Component({
  selector: 'app-budget-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './budget-dashboard.component.html',
  styleUrls: ['./budget-dashboard.component.css'],
})
export class BudgetDashboardComponent implements OnInit {
  stats: BudgetStats | null = null;
  loading = true;
  error = '';

  /** Département déplié pour voir le détail des dépenses. */
  expandedId: string | null = null;
  expenses: BudgetExpense[] = [];
  expensesLoading = false;

  /** Formulaire d'ajout de dépense (inline). */
  newExpense = { label: '', category: 'AUTRE', amount: null as number | null };
  categories = ['SALAIRES', 'RECRUTEMENT', 'FORMATION', 'OUTILS', 'AUTRE'];
  saving = false;

  constructor(private budget: BudgetService) {}

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading = true;
    this.error = '';
    this.budget.getStats().subscribe({
      next: (res) => {
        this.stats = res;
        this.loading = false;
        // Base vide → tenter le seed de démo puis recharger.
        if (!res.departments.length) this.trySeed();
      },
      error: (err) => {
        this.loading = false;
        this.error = err?.error?.detail || 'Impossible de charger les budgets.';
      },
    });
  }

  private trySeed(): void {
    this.budget.seedDemo().subscribe({
      next: (r) => { if (r.created_departments > 0) this.load(); },
      error: () => { /* silencieux : la page reste utilisable, juste vide */ },
    });
  }

  toggleExpenses(dept: DepartmentBudget): void {
    if (this.expandedId === dept.id) {
      this.expandedId = null;
      this.expenses = [];
      return;
    }
    this.expandedId = dept.id;
    this.expenses = [];
    this.expensesLoading = true;
    this.budget.getExpenses(dept.id).subscribe({
      next: (rows) => { this.expenses = rows; this.expensesLoading = false; },
      error: () => { this.expensesLoading = false; },
    });
  }

  addExpense(dept: DepartmentBudget): void {
    if (!this.newExpense.label.trim() || !this.newExpense.amount || this.newExpense.amount <= 0) return;
    this.saving = true;
    this.budget.addExpense(dept.id, {
      label: this.newExpense.label.trim(),
      category: this.newExpense.category,
      amount: this.newExpense.amount,
    }).subscribe({
      next: () => {
        this.saving = false;
        this.newExpense = { label: '', category: 'AUTRE', amount: null };
        this.refreshExpanded(dept);
      },
      error: () => { this.saving = false; },
    });
  }

  deleteExpense(dept: DepartmentBudget, expense: BudgetExpense): void {
    this.budget.deleteExpense(expense.id).subscribe({
      next: () => this.refreshExpanded(dept),
    });
  }

  private refreshExpanded(dept: DepartmentBudget): void {
    // Recharge stats + liste des dépenses du département ouvert.
    this.budget.getStats().subscribe({ next: (res) => (this.stats = res) });
    this.budget.getExpenses(dept.id).subscribe({ next: (rows) => (this.expenses = rows) });
  }

  utilizationTone(pct: number): string {
    if (pct >= 90) return 'danger';
    if (pct >= 70) return 'warn';
    return 'success';
  }

  categoryIcon(cat: string): string {
    return ({
      SALAIRES: '💰', RECRUTEMENT: '🎯', FORMATION: '🎓', OUTILS: '🛠️', AUTRE: '📎',
    } as Record<string, string>)[cat] || '📎';
  }

  trackDept(_i: number, d: DepartmentBudget): string { return d.id; }
}
