import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { EmployeeService } from '../../../core/services/employee.service';
import { Employee } from '../../../core/models/employee.model';

@Component({
  selector: 'app-employee-form',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './employee-form.component.html',
  styleUrls: ['./employee-form.component.css'],
})
export class EmployeeFormComponent implements OnInit {
  employee: Partial<Employee> = { status: 'active' };
  isEdit = false;
  loading = false;
  saving = false;
  error = '';

  departments = ['Tech', 'Data', 'RH', 'Marketing', 'Commercial', 'Finance', 'Support'];

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private employeeService: EmployeeService,
  ) {}

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.isEdit = true;
      this.loading = true;
      this.employeeService.getEmployee(id).subscribe({
        next: (data) => {
          // hireDate → format yyyy-MM-dd attendu par <input type="date">
          this.employee = {
            ...data,
            hireDate: data.hireDate ? (String(data.hireDate).slice(0, 10) as any) : undefined,
          };
          this.loading = false;
        },
        error: (err) => {
          this.loading = false;
          this.error = err?.error?.detail || 'Employé introuvable.';
        },
      });
    }
  }

  submitForm(): void {
    if (!this.employee.firstName || !this.employee.lastName || !this.employee.email) {
      this.error = 'Prénom, nom et email sont obligatoires.';
      return;
    }
    this.saving = true;
    this.error = '';

    const done = {
      next: () => this.router.navigate(['/admin/employees']),
      error: (err: any) => {
        this.saving = false;
        this.error = err?.error?.detail || 'Enregistrement impossible.';
      },
    };

    if (this.isEdit && this.employee.id) {
      this.employeeService.updateEmployee(this.employee.id, this.employee as Employee).subscribe(done);
    } else {
      this.employeeService.createEmployee(this.employee as Employee).subscribe(done);
    }
  }
}
