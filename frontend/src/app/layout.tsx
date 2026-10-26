import type { Metadata } from 'next';
import './globals.css';
import Navbar from '@/components/Navbar';

export const metadata: Metadata = {
  title: 'ULAVU (உழவு) — Voice & SMS Agricultural Lead-Routing',
  description: 'A live voice-and-SMS telephony system connecting Tamil Nadu farmers with nearby agricultural produce buyers and retail mandis.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col bg-[#FAF9F6] text-stone-900 antialiased selection:bg-ochre-200 selection:text-agri-900">
        <Navbar />
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
          {children}
        </main>
        <footer className="border-t border-agri-200/60 bg-white/70 py-6 mt-12 text-center text-xs text-stone-500">
          <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
            <p>
              <strong>ULAVU (உழவு)</strong> &bull; Tamil Nadu Agricultural Telephony Network &bull; Exotel &amp; PostGIS Powered
            </p>
            <p className="text-stone-400">
              Madurantakam &bull; Chengalpattu &bull; Kanchipuram &bull; Tirukalukundram
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
