import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';

@Injectable({
  providedIn: 'root'
})
export class AgentService {
  constructor(private apiService: ApiService) {}

  getAgents(): Observable<any[]> {
    return this.apiService.get<any[]>('agents');
  }

  getAgent(id: string): Observable<any> {
    return this.apiService.get<any>(`agents/${id}`);
  }

  createAgent(agent: any): Observable<any> {
    return this.apiService.post<any>('agents', agent);
  }

  updateAgent(id: string, agent: any): Observable<any> {
    return this.apiService.put<any>(`agents/${id}`, agent);
  }

  deleteAgent(id: string): Observable<void> {
    return this.apiService.delete<void>(`agents/${id}`);
  }
}
