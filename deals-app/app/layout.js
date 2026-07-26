import './globals.css';

export const metadata = {
  title: 'DealHawk — Real-Time Deals from Amazon, Flipkart, Myntra & Ajio',
  description: 'Catch the best deals in real-time from top Indian stores. Huge discounts on electronics, fashion, and home products.',
  keywords: 'deals, discounts, amazon deals, flipkart deals, myntra deals, ajio deals, india shopping',
  openGraph: {
    title: 'DealHawk — Real-Time Deals',
    description: 'Best deals from top Indian stores in real-time.',
    type: 'website',
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
