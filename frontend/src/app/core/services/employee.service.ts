import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Employee } from '../models/employee.model';
import { ApiService } from './api.service';

@Injectable({
  providedIn: 'root'
})
export class EmployeeService {
  constructor(private apiService: ApiService) {}

  getEmployees(): Observable<Employee[]> {
    return this.apiService.get<Employee[]>('employees');
  }

  getEmployee(id: string): Observable<Employee> {
    return this.apiService.get<Employee>(`employees/${id}`);
  }

  createEmployee(employee: Employee): Observable<Employee> {
    return this.apiService.post<Employee>('employees', employee);
  }

  updateEmployee(id: string, employee: Employee): Observable<Employee> {
    return this.apiService.put<Employee>(`employees/${id}`, employee);
  }

  deleteEmployee(id: string): Observable<void> {
    return this.apiService.delete<void>(`employees/${id}`);
  }
}
