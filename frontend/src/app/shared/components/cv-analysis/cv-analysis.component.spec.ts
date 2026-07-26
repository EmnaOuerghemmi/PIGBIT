import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CVAnalysisComponent } from './cv-analysis.component';

describe('CVAnalysisComponent', () => {
  let component: CVAnalysisComponent;
  let fixture: ComponentFixture<CVAnalysisComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CVAnalysisComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(CVAnalysisComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
