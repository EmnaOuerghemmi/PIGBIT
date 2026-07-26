import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CandidateRankingComponent } from './candidate-ranking.component';

describe('CandidateRankingComponent', () => {
  let component: CandidateRankingComponent;
  let fixture: ComponentFixture<CandidateRankingComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CandidateRankingComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(CandidateRankingComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
