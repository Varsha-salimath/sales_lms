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
					50: '#E6F2FF',
					100: '#CCE5FF',
					200: '#99CAFF',
					300: '#67B0FF',
					400: '#3395FF',
					500: '#027BFF',
					600: '#0062CC',
					700: '#004A99',
					800: '#013166',
					900: '#00254C',
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
