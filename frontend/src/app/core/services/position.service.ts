import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { Position } from '../models/position.model';
import { ApiService } from './api.service';

@Injectable({
  providedIn: 'root'
})
export class PositionService {
  constructor(private apiService: ApiService) {}

  getPositions(): Observable<Position[]> {
    return this.apiService.get<Position[]>('positions');
  }

  getPosition(id: string): Observable<Position> {
    return this.apiService.get<Position>(`positions/${id}`);
  }

  createPosition(position: Position): Observable<Position> {
    return this.apiService.post<Position>('positions', position);
  }

  updatePosition(id: string, position: Position): Observable<Position> {
    return this.apiService.put<Position>(`positions/${id}`, position);
  }

  deletePosition(id: string): Observable<void> {
    return this.apiService.delete<void>(`positions/${id}`);
  }
}
