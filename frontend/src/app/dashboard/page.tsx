'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { api, Retailer, SystemStats } from '@/lib/api';
import StatsStrip from '@/components/StatsStrip';
import RetailerCard from '@/components/RetailerCard';
import {
  PlusCircle,
  RefreshCw,
  Search,
  Filter,
  PhoneCall,
  Sparkles,
  Layers,
  CheckCircle2,
} from 'lucide-react';

export default function DashboardPage() {
  const [retailers, setRetailers] = useState<Retailer[]>([]);
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'ACTIVE' | 'PAUSED'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [showWebhookGuide, setShowWebhookGuide] = useState(false);

  const loadData = async (isRefresh = false) => {
    try {
      if (isRefresh) setRefreshing(true);
      else setLoading(true);

      const [retailerList, statsData] = await Promise.all([
        api.getRetailers(),
        api.getStats(),
      ]);

      setRetailers(retailerList);
      setStats(statsData);
    } catch (err: any) {
      console.error('Failed to load dashboard data:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleStatusToggled = (id: string, newActiveState: boolean) => {
    setRetailers((prev) =>
      prev.map((r) => (r.id === id ? { ...r, is_active: newActiveState } : r))
    );
    // Reload stats in background
    api.getStats().then(setStats).catch(() => {});
  };

  const filteredRetailers = retailers.filter((r) => {
    if (statusFilter === 'ACTIVE' && !r.is_active) return false;
    if (statusFilter === 'PAUSED' && r.is_active) return false;

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchName = r.business_name.toLowerCase().includes(q);
      const matchLocation = (r.location_name || '').toLowerCase().includes(q);
      const matchOwner = (r.owner_name || '').toLowerCase().includes(q);
      const matchCrop = (r.accepted_crops || []).some((c) => c.toLowerCase().includes(q));
      return matchName || matchLocation || matchOwner || matchCrop;
    }

    return true;
  });

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-gradient-to-br from-agri-600 via-agri-500 to-agri-700 rounded-3xl p-6 sm:p-8 text-white shadow-xl shadow-agri-900/10 relative overflow-hidden">
        {/* Subtle background graphics */}
        <div className="absolute -right-12 -bottom-12 w-64 h-64 rounded-full bg-white/5 pointer-events-none blur-2xl"></div>
        <div className="absolute right-1/4 top-0 w-48 h-48 rounded-full bg-ochre-400/10 pointer-events-none blur-3xl"></div>

        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="max-w-2xl space-y-2">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 text-ochre-300 text-xs font-bold tracking-wide uppercase">
              <Sparkles className="w-3.5 h-3.5 text-ochre-400" />
              <span>Real-Time Voice Lead Router</span>
            </div>
            <h1 className="text-2xl sm:text-4xl font-extrabold tracking-tight">
              Retailer Network &amp; Demand Hub
            </h1>
            <p className="text-agri-100 text-sm sm:text-base leading-relaxed">
              Managing wholesale agricultural buyers across Tamil Nadu. Farmers call our Exotel IVR in Tamil, select crops and locations using keypad input, our PostGIS engine computes proximity matches within 25km, and leads dispatch instantly via SMS.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => setShowWebhookGuide(!showWebhookGuide)}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs sm:text-sm font-semibold border border-white/20 transition-all backdrop-blur"
            >
              <PhoneCall className="w-4 h-4 text-ochre-300" />
              <span>{showWebhookGuide ? 'Hide Telephony Info' : 'Telephony & Webhook Info'}</span>
            </button>

            <Link
              href="/register"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-ochre-400 hover:bg-ochre-300 text-agri-950 text-xs sm:text-sm font-bold shadow-lg shadow-ochre-900/20 transition-all transform active:scale-95"
            >
              <PlusCircle className="w-4 h-4" />
              <span>Register Retailer</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Telephony & Webhook Instruction Card (Collapsible) */}
      {showWebhookGuide && (
        <div className="bg-white rounded-2xl p-6 border border-agri-200 shadow-sm space-y-4 transition-all">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-agri-900 font-bold text-base">
              <PhoneCall className="w-5 h-5 text-agri-600" />
              <span>Live Exotel Telephony Setup &amp; Call Flow</span>
            </div>
            <span className="text-xs px-2.5 py-1 rounded bg-agri-100 text-agri-800 font-semibold">
              Webhook: /voice/exotel &bull; WS: /voice/exotel/ws
            </span>
          </div>

          <p className="text-xs text-stone-600 leading-relaxed">
            When a farmer calls your Exotel virtual number, Exotel connects to your IVR webhook / Voicebot stream. Farmers press digits (1-9) for crops and locations, PostGIS finds nearby retailers, announces them as Shop 1, Shop 2, etc., and reads phone numbers slowly digit-by-digit.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2 text-xs">
            <div className="p-3 bg-stone-50 rounded-xl border border-stone-200">
              <strong className="text-stone-900 block mb-1">Step 1: Crop Selection</strong>
              <code className="text-agri-700 block font-mono text-[11px]">Keypad Digits 1 - 9</code>
              <span className="text-stone-500">Farmers press 1 for Onion, 2 for Tomato, 3 for Potato, etc.</span>
            </div>

            <div className="p-3 bg-stone-50 rounded-xl border border-stone-200">
              <strong className="text-stone-900 block mb-1">Step 2: Farm Location</strong>
              <code className="text-agri-700 block font-mono text-[11px]">Keypad Digits 1 - 9</code>
              <span className="text-stone-500">Farmers press 1 for Madurantakam, 2 for Chengalpattu, etc.</span>
            </div>

            <div className="p-3 bg-stone-50 rounded-xl border border-stone-200">
              <strong className="text-stone-900 block mb-1">Step 3: Multi-Shop Announcement</strong>
              <code className="text-agri-700 block font-mono text-[11px]">Shop 1, Shop 2 Audio</code>
              <span className="text-stone-500">PostGIS ranks matches &lt;25km, reads phone numbers with pauses, and dispatches SMS!</span>
            </div>
          </div>
        </div>
      )}

      {/* KPI Stats Strip */}
      <StatsStrip stats={stats} loading={loading} />

      {/* Search, Filters, and Refresh Controls */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-white p-4 rounded-2xl border border-stone-200 shadow-sm">
        {/* Search input */}
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-stone-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search by name, crop, or town..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-4 py-2 rounded-xl text-sm border border-stone-200 focus:outline-none focus:ring-2 focus:ring-agri-500 focus:border-transparent bg-stone-50 placeholder:text-stone-400"
          />
        </div>

        {/* Status Filter Tabs & Refresh */}
        <div className="flex items-center gap-2 self-end sm:self-center">
          <div className="inline-flex p-1 bg-stone-100 rounded-xl border border-stone-200 text-xs font-semibold">
            {(['ALL', 'ACTIVE', 'PAUSED'] as const).map((filter) => (
              <button
                key={filter}
                onClick={() => setStatusFilter(filter)}
                className={`px-3 py-1.5 rounded-lg transition-all ${
                  statusFilter === filter
                    ? 'bg-white text-agri-800 shadow-sm'
                    : 'text-stone-600 hover:text-stone-900'
                }`}
              >
                {filter === 'ALL' ? 'All Retailers' : filter === 'ACTIVE' ? 'Active' : 'Paused'}
              </button>
            ))}
          </div>

          <button
            onClick={() => loadData(true)}
            disabled={refreshing}
            className="p-2 rounded-xl border border-stone-200 hover:bg-stone-50 text-stone-600 transition-colors disabled:opacity-50"
            title="Refresh network data"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin text-agri-600' : ''}`} />
          </button>
        </div>
      </div>

      {/* Retailers List */}
      <div className="space-y-4">
        <div className="flex items-center justify-between text-xs font-semibold text-stone-500 px-1">
          <span>Showing {filteredRetailers.length} registered retailer{filteredRetailers.length === 1 ? '' : 's'}</span>
          <span>Click any card to expand leads</span>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
            {[...Array(4)].map((_, i) => (
              <div
                key={i}
                className="bg-white rounded-2xl p-6 border border-stone-200 shadow-sm animate-pulse space-y-4"
              >
                <div className="h-6 bg-stone-200 rounded w-1/2"></div>
                <div className="h-4 bg-stone-200 rounded w-1/3"></div>
                <div className="h-4 bg-stone-200 rounded w-2/3"></div>
                <div className="flex gap-2">
                  <div className="h-6 bg-stone-200 rounded w-16"></div>
                  <div className="h-6 bg-stone-200 rounded w-16"></div>
                </div>
              </div>
            ))}
          </div>
        ) : filteredRetailers.length === 0 ? (
          <div className="bg-white rounded-2xl p-12 text-center border border-stone-200 shadow-sm">
            <div className="w-12 h-12 rounded-full bg-agri-50 text-agri-600 flex items-center justify-center mx-auto mb-4">
              <Layers className="w-6 h-6" />
            </div>
            <h3 className="text-base font-bold text-stone-800">No retailers match your filters</h3>
            <p className="text-xs text-stone-500 mt-1 max-w-sm mx-auto">
              Try adjusting your search query or status filter, or register a new retailer to expand your network.
            </p>
            <Link
              href="/register"
              className="inline-flex items-center gap-2 mt-4 px-4 py-2 rounded-xl bg-agri-600 hover:bg-agri-700 text-white text-xs font-semibold transition-colors"
            >
              <PlusCircle className="w-4 h-4" />
              <span>Register New Retailer</span>
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
            {filteredRetailers.map((retailer) => (
              <RetailerCard
                key={retailer.id}
                retailer={retailer}
                onStatusToggled={handleStatusToggled}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
