'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Sprout, PlusCircle, LayoutDashboard, PhoneCall } from 'lucide-react';

export default function Navbar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-40 bg-[#FAF9F6]/95 backdrop-blur border-b border-agri-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 sm:h-20">
          {/* Logo & Bilingual Brand */}
          <Link href="/dashboard" className="flex items-center gap-3 group">
            <div className="w-10 h-10 sm:w-11 sm:h-11 rounded-xl bg-gradient-to-br from-agri-500 to-agri-600 text-white flex items-center justify-center shadow-md shadow-agri-600/20 group-hover:scale-105 transition-transform">
              <Sprout className="w-6 h-6 text-ochre-400" />
            </div>
            <div>
              <div className="flex items-baseline gap-2">
                <span className="text-xl sm:text-2xl font-black tracking-tight text-agri-900 font-sans">
                  ULAVU
                </span>
                <span className="text-lg sm:text-xl font-bold text-agri-500 font-serif">
                  (உழவு)
                </span>
              </div>
              <p className="text-[11px] sm:text-xs text-stone-500 font-medium tracking-wide">
                Voice &amp; SMS Agricultural Lead Dispatch
              </p>
            </div>
          </Link>

          {/* Navigation & Telephony Status */}
          <div className="flex items-center gap-3 sm:gap-5">
            {/* Live Telephony Indicator */}
            <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full bg-agri-100 border border-agri-300 text-agri-800 text-xs font-semibold">
              <span className="w-2 h-2 rounded-full bg-agri-500 animate-ping"></span>
              <PhoneCall className="w-3.5 h-3.5 text-agri-600" />
              <span>Exotel Telephony Active</span>
            </div>

            {/* Navigation links */}
            <nav className="flex items-center gap-2">
              <Link
                href="/dashboard"
                className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-sm font-semibold transition-all ${
                  pathname === '/dashboard'
                    ? 'bg-agri-500 text-white shadow-sm shadow-agri-600/30'
                    : 'text-stone-700 hover:text-agri-700 hover:bg-agri-100/70'
                }`}
              >
                <LayoutDashboard className="w-4 h-4" />
                <span>Dashboard</span>
              </Link>

              <Link
                href="/register"
                className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-sm font-semibold transition-all ${
                  pathname === '/register'
                    ? 'bg-agri-500 text-white shadow-sm shadow-agri-600/30'
                    : 'text-stone-700 hover:text-agri-700 hover:bg-agri-100/70'
                }`}
              >
                <PlusCircle className="w-4 h-4" />
                <span>Register Retailer</span>
              </Link>
            </nav>
          </div>
        </div>
      </div>
    </header>
  );
}
