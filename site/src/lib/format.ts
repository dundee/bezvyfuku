const MESICE = [
	'leden', 'únor', 'březen', 'duben', 'květen', 'červen',
	'červenec', 'srpen', 'září', 'říjen', 'listopad', 'prosinec',
];

/** '2026-10' -> 'říjen 2026' */
export function nazevMesice(m: string): string {
	return `${MESICE[Number(m.slice(5, 7)) - 1]} ${m.slice(0, 4)}`;
}

/** '2026-10' -> '10/2026' */
export function kratkyMesic(m: string): string {
	return `${Number(m.slice(5, 7))}/${m.slice(0, 4)}`;
}

/** '2026-11-01' -> '1. 11. 2026' */
export function datum(d: string): string {
	return `${Number(d.slice(8, 10))}. ${Number(d.slice(5, 7))}. ${d.slice(0, 4)}`;
}

export function velkym(s: string): string {
	return s.charAt(0).toUpperCase() + s.slice(1);
}

const CISLO = new Intl.NumberFormat('cs-CZ');
const PODIL = new Intl.NumberFormat('cs-CZ', {
	style: 'percent',
	minimumFractionDigits: 1,
	maximumFractionDigits: 1,
});
const ZMENA = new Intl.NumberFormat('cs-CZ', {
	style: 'percent',
	maximumFractionDigits: 0,
	signDisplay: 'exceptZero',
});

export const cislo = (n: number) => CISLO.format(n);
export const podil = (x: number) => PODIL.format(x);

/** Mezirocni zmena, pomlcka kdyz pred rokem nebylo s cim srovnat. */
export const zmena = (ted: number, loni: number) => (loni ? ZMENA.format(ted / loni - 1) : '–');
