'use client';

import React, { useState } from 'react';
import { Retailer, api } from '@/lib/api';
import { MapPin, Phone, User, ChevronDown, ChevronUp, Bell, CheckCircle, PauseCircle } from 'lucide-react';
import LeadsList from './LeadsList';

interface RetailerCardProps {
  retailer: Retailer;
  onStatusToggled: (id: string, newActiveState: boolean) => void;
}

const CROP_EMOJIS: Record<string, string> = {
  onion: '🧅 Onion',
  tomato: '🍅 Tomato',
  potato: '🥔 Potato',
  brinjal: '🍆 Brinjal',
  carrot: '🥕 Carrot',
  cabbage: '🥬 Cabbage',
  cauliflower: '🥦 Cauliflower',
  okra: '🥒 Okra',
  chilli: '🌶️ Green Chilli',
};

export default function RetailerCard({ retailer, onStatusToggled }: RetailerCardProps) {
  const [isActive, setIsActive] = useState(retailer.is_active);
  const [isToggling, setIsToggling] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const handleToggleStatus = async () => {
    try {
      setIsToggling(true);
      const nextState = !isActive;
      // Optimistic update
      setIsActive(nextState);
      const res = await api.toggleRetailerStatus(retailer.id);
      setIsActive(res.is_active);
      onStatusToggled(retailer.id, res.is_active);
    } catch (err: any) {
      // Revert on error
      setIsActive(!isActive);
      alert(`Could not toggle status: ${err.message}`);
    } finally {
      setIsToggling(false);
    }
  };

  return (
    <div
      className={`rounded-2xl border transition-all duration-200 bg-white overflow-hidden shadow-sm ${
        isActive
          ? 'border-stone-200 hover:border-agri-400/80 shadow-agri-900/5'
          : 'border-stone-200/60 opacity-80 bg-stone-50/40'
      }`}
    >
      {/* Top Card Body */}
      <div className="p-5 sm:p-6">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          {/* Main info */}
          <div className="space-y-1.5">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-lg sm:text-xl font-bold text-stone-900 tracking-tight">
                {retailer.business_name}
              </h3>

              {isActive ? (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">
                  <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
                  Active Buyer
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-stone-200 text-stone-700">
                  <PauseCircle className="w-3.5 h-3.5 text-stone-500" />
                  Paused
                </span>
              )}
            </div>

            {retailer.owner_name && (
              <p className="text-xs text-stone-500 flex items-center gap-1.5 font-medium">
                <User className="w-3.5 h-3.5 text-stone-400" />
                <span>Proprietor: <strong className="text-stone-700">{retailer.owner_name}</strong></span>
              </p>
            )}

            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-stone-600 pt-1">
              <span className="flex items-center gap-1 text-agri-800 font-medium">
                <MapPin className="w-3.5 h-3.5 text-ochre-600" />
                <span>{retailer.location_name || 'Tamil Nadu'}</span>
              </span>

              <span className="flex items-center gap-1 text-stone-700 font-mono font-medium">
                <Phone className="w-3.5 h-3.5 text-agri-600" />
                <span>{retailer.phone_number}</span>
              </span>
            </div>
          </div>

          {/* ACTIVE / PAUSED Toggle Switch */}
          <div className="flex items-center gap-3 self-end sm:self-start bg-stone-50 p-2 rounded-xl border border-stone-200/80">
            <span className="text-xs font-semibold uppercase tracking-wider text-stone-500">
              {isActive ? (
                <span className="text-agri-700">ACTIVE</span>
              ) : (
                <span className="text-stone-400">PAUSED</span>
              )}
            </span>
            <button
              onClick={handleToggleStatus}
              disabled={isToggling}
              type="button"
              role="switch"
              aria-checked={isActive}
              className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-agri-500 focus:ring-offset-2 ${
                isActive ? 'bg-agri-500' : 'bg-stone-300'
              } ${isToggling ? 'opacity-50 cursor-wait' : ''}`}
            >
              <span
                className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                  isActive ? 'translate-x-5' : 'translate-x-0'
                }`}
              />
            </button>
          </div>
        </div>

        {/* Accepted Crops Chips */}
        <div className="mt-4 pt-3 border-t border-stone-100">
          <p className="text-[11px] font-bold text-stone-400 uppercase tracking-wider mb-2">
            Accepted Crops:
          </p>
          <div className="flex flex-wrap gap-1.5">
            {retailer.accepted_crops && retailer.accepted_crops.length > 0 ? (
              retailer.accepted_crops.map((crop) => (
                <span
                  key={crop}
                  className="inline-flex items-center px-2.5 py-1 rounded-lg text-xs font-semibold bg-agri-50 border border-agri-200 text-agri-900"
                >
                  {CROP_EMOJIS[crop.toLowerCase()] || `🌱 ${crop}`}
                </span>
              ))
            ) : (
              <span className="text-xs text-stone-400 italic">No crops configured</span>
            )}
          </div>
        </div>
      </div>

      {/* Expandable Leads Panel Button */}
      <div className="bg-stone-50/80 border-t border-stone-200/80 px-5 sm:px-6 py-3 flex items-center justify-between">
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-2 text-xs font-bold text-agri-800 hover:text-agri-600 transition-colors"
        >
          <Bell className="w-3.5 h-3.5 text-ochre-600" />
          <span>Incoming Farmer Leads</span>
          {retailer.leads_count !== undefined && retailer.leads_count > 0 && (
            <span className="px-2 py-0.5 rounded-full text-[10px] font-black bg-agri-600 text-white">
              {retailer.leads_count}
            </span>
          )}
          {expanded ? (
            <ChevronUp className="w-4 h-4 ml-1" />
          ) : (
            <ChevronDown className="w-4 h-4 ml-1" />
          )}
        </button>

        <span className="text-[11px] text-stone-400 font-medium">
          {isActive ? 'Routing calls & SMS' : 'Temporarily suspended'}
        </span>
      </div>

      {/* Expanded Leads Drawer */}
      {expanded && (
        <div className="p-5 sm:p-6 bg-stone-50 border-t border-stone-200">
          <LeadsList retailerId={retailer.id} retailerName={retailer.business_name} />
        </div>
      )}
    </div>
  );
}
