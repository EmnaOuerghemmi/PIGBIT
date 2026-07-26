import { Pipe, PipeTransform } from '@angular/core';

@Pipe({
  name: 'currencyTnd',
  standalone: true
})
export class CurrencyTndPipe implements PipeTransform {
  transform(value: number, ...args: any[]): string {
    if (value === null || value === undefined) {
      return '';
    }
    return new Intl.NumberFormat('fr-TN', {
      style: 'currency',
      currency: 'TND'
    }).format(value);
  }
}
