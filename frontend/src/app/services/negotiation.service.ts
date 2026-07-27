// negotiation.service.ts
// À placer dans: frontend/src/app/services/negotiation.service.ts

import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, Subject } from 'rxjs';
import { environment } from '../../environments/environment';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';
import { tap } from 'rxjs/operators';

export interface JobData {
  job_id: string;
  title: string;
  description: string;
  rating?: number;
  company_age?: number;
  competitors_count?: number;
  python?: number;
  spark?: number;
  aws?: number;
  excel?: number;
  is_hourly?: number;
  same_state?: number;
  employee_provided?: number;
  experience_years?: number | null;
  skills_text?: string;
}

export interface NegotiationRequest {
  candidate_id: string;
  job_data: JobData;
  employer_offer: number;
}

export interface NegotiationMessage {
  type: string;
  [key: string]: any;
}

@Injectable({
  providedIn: 'root'
})
export class NegotiationService {
  private apiUrl = `${environment.apiUrl}/negotiations`;
  private wsSubject: WebSocketSubject<NegotiationMessage> | null = null;
  private messages$ = new Subject<NegotiationMessage>();

  constructor(private http: HttpClient) {}

  /**
   * Lance une négociation automatique
   */
  initiateNegotiation(request: NegotiationRequest): Observable<any> {
    return this.http.post(`${this.apiUrl}/initiate`, request).pipe(
      tap(response => {
      })
    );
  }

  /**
   * Traite une contre-offre employeur
   */
  processCounterOffer(jobId: string, employerOffer: number, predictedSalary: number, confidence: number): Observable<any> {
    return this.http.post(`${this.apiUrl}/process-counter-offer`, {
      job_id: jobId,
      employer_offer: employerOffer,
      predicted_salary: predictedSalary,
      confidence: confidence
    });
  }

  /**
   * Récupère le résumé d'une négociation
   */
  getNegotiationSummary(jobId: string): Observable<any> {
    return this.http.get(`${this.apiUrl}/summary/${jobId}`);
  }

  /**
   * Se connecte au WebSocket pour recevoir les mises à jour en temps réel
   */
  connectToNegotiationUpdates(jobId: string): Observable<NegotiationMessage> {
    const wsUrl = `${environment.wsUrl}/negotiations/ws/${jobId}`;
    
    this.wsSubject = webSocket<NegotiationMessage>({
      url: wsUrl,
      openObserver: {
        next: () => {
        }
      },
      closeObserver: {
        next: () => {
          this.wsSubject = null;
        }
      }
    });

    return this.wsSubject.asObservable().pipe(
      tap(message => {
        this.messages$.next(message);
      })
    );
  }

  /**
   * Envoie un message via le WebSocket
   */
  sendMessage(message: NegotiationMessage): void {
    if (this.wsSubject) {
      this.wsSubject.next(message);
    }
  }

  /**
   * Ferme la connexion WebSocket
   */
  disconnectWebSocket(): void {
    if (this.wsSubject) {
      this.wsSubject.complete();
    }
  }

  /**
   * Obtient le stream de messages
   */
  getMessages(): Observable<NegotiationMessage> {
    return this.messages$.asObservable();
  }
}
