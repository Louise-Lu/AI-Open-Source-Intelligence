export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        surface: '#ffffff',
        muted: '#f8fafc',
      },
      boxShadow: {
        soft: '0 10px 30px -18px rgba(15, 23, 42, 0.2)',
      },
    },
  },
  plugins: [],
};
