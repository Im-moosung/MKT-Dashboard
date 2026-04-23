'use client';
import type { PresetChartConfig } from '@/lib/chart-types/registry';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';

// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function TableChart({ data, config: _config }: { data: Record<string, unknown>[]; config: PresetChartConfig }) {
  const columns = data.length > 0 ? Object.keys(data[0]) : [];

  return (
    <div data-chart="table" className="w-full overflow-auto">
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((col) => (
              <TableHead key={col}>{col}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((row, i) => (
            <TableRow key={i}>
              {columns.map((col) => (
                <TableCell key={col}>{String(row[col] ?? '')}</TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
