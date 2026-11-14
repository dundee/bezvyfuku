// Tabulka BEV podle znacek za zvolene obdobi a srovnani s obdobim o rok driv.
// Pouziva ji server pro vychozi stav stranky i skript v prohlizeci.
import { soucet, type Rady } from './data';
import { nazevMesice } from './format';

export type Obdobi = 'mesic' | 'rok' | '12m';

/** Kolik radku tabulka ukazuje, nez si ctenar rozbali vsechny. */
export const ZKRACENE = 20;

export const OBDOBI: Record<Obdobi, string> = {
	mesic: 'Měsíc',
	rok: 'Od začátku roku',
	'12m': 'Posledních 12 měsíců',
};

/** Prvni a posledni index obdobi, ktere konci mesicem i. */
export function rozsah(obdobi: Obdobi, i: number, mesice: string[]): [number, number] {
	if (obdobi === 'mesic') return [i, i];
	if (obdobi === 'rok') return [i - Number(mesice[i].slice(5, 7)) + 1, i];
	return [i - 11, i];
}

export function popisObdobi(obdobi: Obdobi, i: number, mesice: string[]): string {
	const [od, doI] = rozsah(obdobi, i, mesice);
	if (od === doI) return nazevMesice(mesice[doI]);
	return `${nazevMesice(mesice[od])} – ${nazevMesice(mesice[doI])}`;
}

export interface Radek {
	znacka: string;
	ted: number;
	loni: number;
}

export function tabulka(rady: Rady, obdobi: Obdobi, i: number, mesice: string[]) {
	const [od, doI] = rozsah(obdobi, i, mesice);
	const radky: Radek[] = [];
	let ted = 0;
	let loni = 0;
	for (const [znacka, rada] of Object.entries(rady)) {
		const r = { znacka, ted: soucet(rada, od, doI), loni: soucet(rada, od - 12, doI - 12) };
		if (!r.ted && !r.loni) continue;
		radky.push(r);
		ted += r.ted;
		loni += r.loni;
	}
	radky.sort((a, b) => b.ted - a.ted || b.loni - a.loni || a.znacka.localeCompare(b.znacka, 'cs'));
	return { radky, ted, loni };
}

export function nazevZnacky(znacka: string): string {
	return znacka || '(neuvedeno)';
}
