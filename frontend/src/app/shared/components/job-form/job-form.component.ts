import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { JobOffer } from '../../../core/services/recruitment.service';

@Component({
  selector: 'app-job-form',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './job-form.component.html',
  styleUrls: ['./job-form.component.css']
})
export class JobFormComponent implements OnInit {
  @Input() isOpen = false;
  @Input() editingJob: JobOffer | null = null;
  @Output() close = new EventEmitter<void>();
  @Output() submit = new EventEmitter<Partial<JobOffer>>();

  formData: Partial<JobOffer> = {
    title: '',
    description: '',
    salary_min: undefined,
    salary_max: undefined,
    is_active: true
  };

  isSubmitting = false;
  isEditing = false;
  successMsg = '';
  errorMsg = '';

  ngOnInit() {
    if (this.editingJob) {
      this.isEditing = true;
      this.formData = { ...this.editingJob };
    }
  }

  closeForm() {
    this.resetForm();
    this.close.emit();
  }

  submitForm() {
    if (!this.formData.title || !this.formData.description || !this.formData.salary_min || !this.formData.salary_max) {
      this.errorMsg = 'Tous les champs sont requis';
      return;
    }

    this.isSubmitting = true;
    this.errorMsg = '';
    this.successMsg = '';

    this.submit.emit(this.formData);

    setTimeout(() => {
      this.isSubmitting = false;
      this.successMsg = 'Offre sauvegardée avec succès!';
      setTimeout(() => this.closeForm(), 1500);
    }, 1000);
  }

  resetForm() {
    this.formData = {
      title: '',
      description: '',
      salary_min: undefined,
      salary_max: undefined,
      is_active: true
    };
    this.isEditing = false;
    this.successMsg = '';
    this.errorMsg = '';
  }
}
