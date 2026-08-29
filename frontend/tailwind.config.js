import frappeUIPreset from 'frappe-ui/tailwind'

export default {
	presets: [frappeUIPreset],
	content: [
		'./index.html',
		'./src/**/*.{vue,js,ts,jsx,tsx}',
		'./node_modules/frappe-ui/src/**/*.{vue,js,ts,jsx,tsx}',
		'../node_modules/frappe-ui/src/**/*.{vue,js,ts,jsx,tsx}',
		'./node_modules/frappe-ui/frappe/**/*.{vue,js,ts,jsx,tsx}',
		'../node_modules/frappe-ui/frappe/**/*.{vue,js,ts,jsx,tsx}',
	],
	theme: {
		extend: {
			colors: {
				blue: {
					50: '#E8EDF9',
					100: '#E8EDF9',
					200: '#C5D0E8',
					300: '#8FA3D0',
					400: '#3D5A9E',
					500: '#1B3F8B',
					600: '#1B3F8B',
					700: '#132D6B',
					800: '#132D6B',
					900: '#0D1F4A',
				},
				orange: {
					50: '#FEF0E6',
					100: '#FEF0E6',
					200: '#FBD4B8',
					300: '#F8A866',
					400: '#F47A20',
					500: '#F47A20',
					600: '#D4600A',
					700: '#D4600A',
					800: '#B04D08',
					900: '#8A3D06',
				},
			},
			strokeWidth: {
				1.5: '1.5',
			},
			screens: {
				'2xl': '1600px',
				'3xl': '1920px',
			},
		},
	},
	plugins: [],
}
