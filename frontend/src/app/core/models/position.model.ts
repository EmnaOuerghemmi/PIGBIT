export interface Position {
  id: string;
  title: string;
  department: string;
  description: string;
  requirements: string[];
  salary: number;
  status: 'open' | 'closed' | 'filled';
  createdAt: Date;
  updatedAt: Date;
}
