'use client';

import React, { useState, useEffect } from 'react';
import { InquiryLog, api } from '@/lib/api';
import { Phone, MapPin, Check, X, Clock, AlertCircle } from 'lucide-react';

interface LeadsListProps {
  retailerId: string;
  retailerName: string;
}

const CROP_EMOJIS: Record<string, string> = {
  onion: '🧅',
  tomato: '🍅',
  potato: '🥔',
  brinjal: '🍆',
  carrot: '🥕',
  cabbage: '🥬',
  cauliflower: '🥦',
  okra: '🥒',
  chilli: '🌶️',
};

export default function LeadsList({ retailerId, retailerName }: LeadsListProps) {
  const [leads, setLeads] = useState<InquiryLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchLeads = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getRetailerLeads(retailerId);
      setLeads(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch incoming leads');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeads();
  }, [retailerId]);

  const handleStatusUpdate = async (
    inquiryId: string,
    newStatus: 'SOLD' | 'NOT_INTERESTED'
  ) => {
    try {
      setUpdatingId(inquiryId);
      const updated = await api.updateInquiryStatus(inquiryId, newStatus);
      setLeads((prev) =>
        prev.map((item) => (item.id === inquiryId ? updated : item))
      );
    } catch (err: any) {
      alert(`Could not update lead status: ${err.message}`);
    } finally {
      setUpdatingId(null);
    }
  };

  if (loading) {
    return (
      <div className="py-6 space-y-3">
        {[...Array(2)].map((_, i) => (
          <div
            key={i}
            className="p-4 rounded-xl border border-stone-100 bg-stone-50 animate-pulse flex items-center justify-between"
          >
            <div className="space-y-2 w-1/2">
              <div className="h-4 bg-stone-200 rounded w-1/3"></div>
              <div className="h-3 bg-stone-200 rounded w-2/3"></div>
            </div>
            <div className="h-8 bg-stone-200 rounded w-24"></div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="py-4 px-4 bg-rose-50 text-rose-700 rounded-xl text-sm flex items-center gap-2">
        <AlertCircle className="w-4 h-4 shrink-0" />
        <span>{error}</span>
      </div>
    );
  }

  if (leads.length === 0) {
    return (
      <div className="py-8 text-center text-stone-500 bg-stone-50/70 rounded-xl border border-dashed border-stone-200">
        <p className="text-sm font-medium">No incoming farmer leads yet for {retailerName}.</p>
        <p className="text-xs text-stone-400 mt-1">
          When a farmer calls Ulavu and asks for matching crops, they will appear here instantly!
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3 pt-2">
      {leads.map((lead) => {
        const crop = (lead.crop_inquired || '').toLowerCase();
        const emoji = CROP_EMOJIS[crop] || '🌱';
        const isPending = lead.status === 'PENDING';
        const isUpdating = updatingId === lead.id;

        return (
          <div
            key={lead.id}
            className="p-4 rounded-xl border border-stone-200 bg-white hover:border-agri-300 transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-sm"
          >
            {/* Left info */}
            <div className="space-y-1.5">
              <div className="flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-agri-100/80 text-agri-900 text-xs font-bold capitalize">
                  <span>{emoji}</span>
                  <span>{lead.crop_inquired || 'Produce'}</span>
                </span>

                <span
                  className={`text-[11px] font-bold px-2.5 py-0.5 rounded-full uppercase tracking-wider ${
                    lead.status === 'SOLD'
                      ? 'bg-emerald-100 text-emerald-800'
                      : lead.status === 'NOT_INTERESTED'
                      ? 'bg-stone-200 text-stone-700'
                      : 'bg-ochre-100 text-ochre-800 animate-pulse'
                  }`}
                >
                  {lead.status === 'SOLD'
                    ? 'Sold / Purchased'
                    : lead.status === 'NOT_INTERESTED'
                    ? 'Not Interested'
                    : 'Pending Response'}
                </span>

                {lead.distance_km !== null && (
                  <span className="text-xs font-semibold text-agri-700 bg-agri-50 px-2 py-0.5 rounded border border-agri-200">
                    {lead.distance_km} km away
                  </span>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-stone-600">
                <span className="flex items-center gap-1 font-mono font-medium">
                  <Phone className="w-3.5 h-3.5 text-stone-400" />
                  {lead.masked_farmer_phone || lead.farmer_phone}
                </span>

                <span className="flex items-center gap-1">
                  <MapPin className="w-3.5 h-3.5 text-ochre-600" />
                  <span>Farm at: <strong className="text-stone-800">{lead.location_spoken || 'Nearby'}</strong></span>
                </span>

                <span className="flex items-center gap-1 text-stone-400">
                  <Clock className="w-3.5 h-3.5" />
                  <span>{new Date(lead.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                </span>
              </div>
            </div>

            {/* Actions for PENDING lead */}
            {isPending && (
              <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
                <button
                  onClick={() => handleStatusUpdate(lead.id, 'SOLD')}
                  disabled={isUpdating}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold shadow-sm transition-all active:scale-95 disabled:opacity-50"
                  title="Mark this inquiry as successfully purchased"
                >
                  <Check className="w-3.5 h-3.5" />
                  <span>Mark as Sold</span>
                </button>

                <button
                  onClick={() => handleStatusUpdate(lead.id, 'NOT_INTERESTED')}
                  disabled={isUpdating}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-stone-100 hover:bg-stone-200 text-stone-700 text-xs font-semibold transition-all active:scale-95 disabled:opacity-50"
                  title="Decline this supply offer"
                >
                  <X className="w-3.5 h-3.5" />
                  <span>Not Interested</span>
                </button>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
