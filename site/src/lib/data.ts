// Mesicni rady z pipeline (python -m pipeline export). Kazda rada je seznam
// poctu zarovnany na `mesice`.
import raw from '../data/registrace.json';

export type Typ = 'nove' | 'ojete';
export type Rady = Record<string, number[]>;

export interface Registrace {
	snapshot: string;
	posledniMesic: string;
	skupinaBev: string;
	mesice: string[];
	pohon: Record<Typ, Rady>;
	bevZnacky: Record<Typ, Rady>;
	bevModely: Record<Typ, Rady>;
	aliasy: Record<string, string>;
}

export const data: Registrace = raw;
export const posledni = data.mesice.length - 1;

/** Soucet vsech rad v mesici i. */
export function celkem(rady: Rady, i: number): number {
	let s = 0;
	for (const rada of Object.values(rady)) s += rada[i] ?? 0;
	return s;
}

/** Soucet rady v mesicich od..doI vcetne, mesice pred zacatkem dat se nepocitaji. */
export function soucet(rada: number[], od: number, doI: number): number {
	let s = 0;
	for (let i = Math.max(od, 0); i <= doI; i++) s += rada[i] ?? 0;
	return s;
}
