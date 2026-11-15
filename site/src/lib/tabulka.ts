// Tabulky BEV podle znacek nebo modelu za zvolene obdobi a srovnani s rokem driv.
// Pouziva je server pro vychozi stav stranky i skript v prohlizeci.
import { soucet, type Rady } from './data';
import { nazevMesice } from './format';

export type Obdobi = 'mesic' | 'rok' | '12m';
export type Zdroj = 'bevZnacky' | 'bevModely';

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
	klic: string;
	ted: number;
	loni: number;
}

export function tabulka(rady: Rady, obdobi: Obdobi, i: number, mesice: string[]) {
	const [od, doI] = rozsah(obdobi, i, mesice);
	const radky: Radek[] = [];
	let ted = 0;
	let loni = 0;
	for (const [klic, rada] of Object.entries(rady)) {
		const r = { klic, ted: soucet(rada, od, doI), loni: soucet(rada, od - 12, doI - 12) };
		if (!r.ted && !r.loni) continue;
		radky.push(r);
		ted += r.ted;
		loni += r.loni;
	}
	radky.sort((a, b) => b.ted - a.ted || b.loni - a.loni || a.klic.localeCompare(b.klic, 'cs'));
	return { radky, ted, loni };
}

export function nazev(s: string): string {
	return s || '(neuvedeno)';
}

/** Klic v `bevModely` ma tvar `ZNAČKA|MODEL`. */
export function rozdelModel(klic: string): [string, string] {
	const sep = klic.indexOf('|');
	return sep === -1 ? [klic, ''] : [klic.slice(0, sep), klic.slice(sep + 1)];
}
