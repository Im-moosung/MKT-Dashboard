'use client';
import { GridLayout } from 'react-grid-layout';
import type { Layout } from 'react-grid-layout';
import 'react-grid-layout/css/styles.css';
import 'react-resizable/css/styles.css';

export interface ChartInstance {
  id: string;
  title: string;
  gridX: number;
  gridY: number;
  gridW: number;
  gridH: number;
}

export function DashboardGrid({
  charts,
  onLayoutChange,
  renderChart,
}: {
  charts: ChartInstance[];
  onLayoutChange: (layout: { i: string; x: number; y: number; w: number; h: number }[]) => void;
  renderChart: (c: ChartInstance) => React.ReactNode;
}) {
  const layout: Layout = charts.map((c) => ({
    i: c.id,
    x: c.gridX,
    y: c.gridY,
    w: c.gridW,
    h: c.gridH,
  }));

  return (
    <GridLayout
      className="layout"
      layout={layout}
      gridConfig={{ cols: 12, rowHeight: 80, margin: [10, 10], containerPadding: null, maxRows: Infinity }}
      width={1200}
      onLayoutChange={(l) =>
        onLayoutChange(
          l.map((item) => ({ i: item.i, x: item.x, y: item.y, w: item.w, h: item.h })),
        )
      }
    >
      {charts.map((c) => (
        <div key={c.id}>{renderChart(c)}</div>
      ))}
    </GridLayout>
  );
}
