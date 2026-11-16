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

export interface IkonaZmeny {
	trida: 'nove' | 'rust' | 'stejne' | 'pokles';
	popis: string;
	d: string;
	plna?: boolean;
}

/** Piktogram zmeny podle cisteho mezirocniho pomeru (shodne se zaokrouhlenym %). */
export function ikonaZmeny(ted: number, loni: number): IkonaZmeny | null {
	if (!loni) {
		return ted > 0
			? {
					trida: 'nove',
					popis: 'Nové oproti loňsku',
					d: 'M8 1.5L9.7 6.3 14.5 8 9.7 9.7 8 14.5 6.3 9.7 1.5 8 6.3 6.3Z',
					plna: true,
				}
			: null;
	}
	const pct = Math.round((ted / loni - 1) * 100);
	if (pct >= 100) {
		return { trida: 'rust', popis: 'Růst o 100 % a více', d: 'M8 13V3M4 7l4-4 4 4' };
	}
	if (pct >= 10) {
		return { trida: 'rust', popis: 'Růst o 10–99 %', d: 'M4 12L12 4M6 4h6v6' };
	}
	if (pct > -10) {
		return { trida: 'stejne', popis: 'Změna do ±9 %', d: 'M3 8h10M9 4l4 4-4 4' };
	}
	if (pct > -50) {
		return { trida: 'pokles', popis: 'Pokles o 10–49 %', d: 'M4 4l8 8M12 6v6H6' };
	}
	return { trida: 'pokles', popis: 'Pokles o 50 % a více', d: 'M8 3v10M4 9l4 4 4-4' };
}
