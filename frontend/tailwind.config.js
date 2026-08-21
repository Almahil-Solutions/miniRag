/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class', '[data-theme="dark"]'],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          900: 'var(--ink-900)',
          800: 'var(--ink-800)',
          700: 'var(--ink-700)',
          400: 'var(--ink-400)',
        },
        paper: {
          0: 'var(--paper-0)',
          100: 'var(--paper-100)',
        },
        line: {
          200: 'var(--line-200)',
          700: 'var(--line-700)',
        },
        accent: {
          100: 'var(--accent-100)',
          400: 'var(--accent-400)',
          500: 'var(--accent-500)',
          600: 'var(--accent-600)',
          700: 'var(--accent-700)',
        },
        success: { 600: 'var(--success-600)' },
        warning: { 600: 'var(--warning-600)' },
        error: { 600: 'var(--error-600)' },
      },
      fontFamily: {
        display: ['var(--font-display)'],
        sans: ['var(--font-sans)'],
        mono: ['var(--font-mono)'],
      },
      borderRadius: {
        sm: 'var(--radius-sm)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
      },
      boxShadow: {
        card: 'var(--shadow-card)',
        modal: 'var(--shadow-modal)',
      },
      fontSize: {
        'display-lg': ['3.5rem', { lineHeight: '1.05' }],
        'display': ['2.25rem', { lineHeight: '1.1' }],
        'h2': ['1.5rem', { lineHeight: '1.25' }],
        'h3': ['1.125rem', { lineHeight: '1.3' }],
        'body': ['1rem', { lineHeight: '1.6' }],
        'sm': ['0.875rem', { lineHeight: '1.5' }],
        'xs': ['0.75rem', { lineHeight: '1.4' }],
        'mono': ['0.875rem', { lineHeight: '1.6' }],
      },
      spacing: {
        '18': '4.5rem',
        '22': '5.5rem',
        '30': '7.5rem',
      },
      maxWidth: {
        'content': '1200px',
      },
    },
  },
  plugins: [],
}