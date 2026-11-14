// Spolecne nastaveni grafu (ECharts, jen pouzite casti kvuli velikosti balicku).
import * as echarts from 'echarts/core';
import { BarChart, LineChart } from 'echarts/charts';
import {
	DataZoomSliderComponent,
	GraphicComponent,
	GridComponent,
	LegendComponent,
	ToolboxComponent,
	TooltipComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { kratkyMesic } from './format';

echarts.use([
	BarChart,
	LineChart,
	DataZoomSliderComponent,
	GraphicComponent,
	GridComponent,
	LegendComponent,
	ToolboxComponent,
	TooltipComponent,
	CanvasRenderer,
]);

export type Volby = echarts.EChartsCoreOption;

export const PISMO = 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif';

export const BARVY: Record<string, string> = {
	'Elektro (BEV)': '#15803d',
	Hybrid: '#84cc16',
	Benzín: '#f59e0b',
	Nafta: '#52525b',
	LPG: '#a855f7',
	CNG: '#0ea5e9',
	Ostatní: '#d4d4d8',
};

/** Graf, ktery se prizpusobi sirce kontejneru. `podleSirky` vraci volby,
 *  ktere zavisi na sirce (napr. misto pro legendu na dva radky na mobilu). */
export function vytvorGraf(el: HTMLElement, podleSirky?: (sirka: number) => Volby): echarts.ECharts {
	const graf = echarts.init(el);
	new ResizeObserver(() => {
		graf.resize();
		if (podleSirky) graf.setOption(podleSirky(el.clientWidth));
	}).observe(el);
	return graf;
}

/** Spolecny zaklad: pismo, stazeni obrazku a podpis webu, at je poznat, odkud graf je. */
export function zaklad(soubor: string): Volby {
	return {
		textStyle: { fontFamily: PISMO },
		animationDuration: 300,
		grid: { left: 8, right: 8, top: 56, bottom: 72 },
		toolbox: {
			top: 0,
			right: 0,
			feature: { saveAsImage: { name: soubor, pixelRatio: 2, title: 'Stáhnout obrázek' } },
		},
		graphic: [
			{
				type: 'text',
				right: 8,
				bottom: 0,
				silent: true,
				style: { text: 'bezvyfuku.cz', fill: '#a1a1aa', font: `12px ${PISMO}` },
			},
		],
	};
}

/** Osa mesicu s popiskem jen u ledna. */
export function osaMesicu(mesice: string[]): Volby {
	return {
		type: 'category',
		data: mesice,
		axisTick: { show: false },
		axisLabel: {
			interval: (_: number, m: string) => m.endsWith('-01'),
			formatter: (m: string) => m.slice(0, 4),
			hideOverlap: true,
		},
	};
}

/** Posuvnik pod grafem, na zacatku vybrany usek od indexu `od`. */
export function posuvnik(mesice: string[], od: number): Volby[] {
	return [
		{
			type: 'slider',
			startValue: od,
			endValue: mesice.length - 1,
			height: 22,
			bottom: 24,
			brushSelect: false,
			labelFormatter: (_: number, m: string) => kratkyMesic(m),
		},
	];
}
