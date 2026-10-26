'use client';

import React from 'react';
import { SystemStats } from '@/lib/api';
import { PhoneIncoming, CheckCircle2, Store, Users } from 'lucide-react';

interface StatsStripProps {
  stats: SystemStats | null;
  loading: boolean;
}

export default function StatsStrip({ stats, loading }: StatsStripProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 my-6">
        {[...Array(4)].map((_, i) => (
          <div
            key={i}
            className="bg-white rounded-2xl p-5 border border-stone-200 shadow-sm animate-pulse"
          >
            <div className="w-10 h-10 rounded-xl bg-stone-200 mb-3"></div>
            <div className="h-4 bg-stone-200 rounded w-2/3 mb-2"></div>
            <div className="h-8 bg-stone-200 rounded w-1/2"></div>
          </div>
        ))}
      </div>
    );
  }

  const statItems = [
    {
      title: 'Inquiries Today',
      value: stats ? stats.total_inquiries_today : 0,
      subtext: 'Incoming calls & routing',
      icon: PhoneIncoming,
      bgColor: 'bg-agri-50',
      iconColor: 'text-agri-600',
      borderColor: 'border-agri-200',
    },
    {
      title: 'Match Rate',
      value: stats ? `${stats.match_rate_percentage}%` : '100%',
      subtext: 'Within 25km radius',
      icon: CheckCircle2,
      bgColor: 'bg-emerald-50',
      iconColor: 'text-emerald-600',
      borderColor: 'border-emerald-200',
    },
    {
      title: 'Active Retailers',
      value: stats ? stats.active_retailer_count : 0,
      subtext: 'Receiving farmer leads',
      icon: Store,
      bgColor: 'bg-ochre-50',
      iconColor: 'text-ochre-700',
      borderColor: 'border-ochre-200',
    },
    {
      title: 'Total Network',
      value: stats ? stats.total_retailers : 0,
      subtext: 'Onboarded buyers',
      icon: Users,
      bgColor: 'bg-amber-50',
      iconColor: 'text-amber-700',
      borderColor: 'border-amber-200',
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6 my-6">
      {statItems.map((item, index) => {
        const Icon = item.icon;
        return (
          <div
            key={index}
            className={`bg-white rounded-2xl p-5 border ${item.borderColor} shadow-sm card-hover flex flex-col justify-between`}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs sm:text-sm font-medium text-stone-500">
                {item.title}
              </span>
              <div
                className={`w-9 h-9 rounded-xl ${item.bgColor} ${item.iconColor} flex items-center justify-center`}
              >
                <Icon className="w-5 h-5" />
              </div>
            </div>
            <div>
              <div className="text-2xl sm:text-3xl font-black text-stone-900 tracking-tight">
                {item.value}
              </div>
              <p className="text-[11px] sm:text-xs text-stone-400 mt-1">
                {item.subtext}
              </p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
