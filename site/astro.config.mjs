// @ts-check
import { defineConfig } from 'astro/config';

// https://astro.build/config
export default defineConfig({
	site: 'https://bezvyfuku.cz',
	vite: {
		build: {
			// ECharts core sam ma ~600 kB (200 kB gzip), mensi uz nebude.
			chunkSizeWarningLimit: 700,
		},
	},
});
