import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { EmployeeService } from '../../../core/services/employee.service';
import { Employee } from '../../../core/models/employee.model';

@Component({
  selector: 'app-employee-detail',
  standalone: true,
  imports: [CommonModule, RouterLink],
  templateUrl: './employee-detail.component.html',
  styleUrls: ['./employee-detail.component.css'],
})
export class EmployeeDetailComponent implements OnInit {
  employee: Employee | null = null;
  loading = true;
  error = '';

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private employeeService: EmployeeService,
  ) {}

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) this.loadEmployee(id);
  }

  loadEmployee(id: string): void {
    this.loading = true;
    this.employeeService.getEmployee(id).subscribe({
      next: (data) => { this.employee = data; this.loading = false; },
      error: (err) => {
        this.loading = false;
        this.error = err?.error?.detail || 'Employé introuvable.';
      },
    });
  }

  remove(): void {
    if (!this.employee) return;
    if (!confirm(`Supprimer la fiche de ${this.employee.firstName} ${this.employee.lastName} ?`)) return;
    this.employeeService.deleteEmployee(this.employee.id).subscribe({
      next: () => this.router.navigate(['/admin/employees']),
      error: () => { this.error = 'Suppression impossible.'; },
    });
  }

  statusLabel(s: string): string {
    return ({ active: 'Actif', inactive: 'Inactif', 'on-leave': 'En congé' } as any)[s] || s;
  }

  get initials(): string {
    if (!this.employee) return '';
    return (this.employee.firstName[0] || '') + (this.employee.lastName[0] || '');
  }
}
