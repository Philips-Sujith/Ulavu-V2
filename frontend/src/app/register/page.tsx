'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { api, RetailerCreateInput } from '@/lib/api';
import {
  ArrowLeft,
  Store,
  User,
  Phone,
  MapPin,
  Check,
  AlertCircle,
  Sparkles,
  Info,
} from 'lucide-react';

const SEEDED_TOWNS = [
  { name: 'Madurantakam', lat: 12.5085, lng: 79.8850, district: 'Chengalpattu District' },
  { name: 'Chengalpattu', lat: 12.6841, lng: 79.9836, district: 'Chengalpattu District' },
  { name: 'Kanchipuram', lat: 12.8342, lng: 79.7036, district: 'Kanchipuram District' },
  { name: 'Tirukalukundram', lat: 12.6105, lng: 80.0537, district: 'Chengalpattu District' },
];

const AVAILABLE_CROPS = [
  { id: 'tomato', name: 'Tomato', tamil: 'தக்காளி', emoji: '🍅' },
  { id: 'onion', name: 'Onion', tamil: 'வெங்காயம்', emoji: '🧅' },
  { id: 'brinjal', name: 'Brinjal', tamil: 'கத்தரிக்காய்', emoji: '🍆' },
  { id: 'chilli', name: 'Chilli', tamil: 'மிளகாய்', emoji: '🌶️' },
  { id: 'okra', name: 'Okra', tamil: 'வெண்டைக்காய்', emoji: '🥬' },
];

export default function RegisterPage() {
  const router = useRouter();

  const [businessName, setBusinessName] = useState('');
  const [ownerName, setOwnerName] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [selectedTown, setSelectedTown] = useState(SEEDED_TOWNS[0].name);
  const [selectedCrops, setSelectedCrops] = useState<string[]>(['tomato', 'onion']);
  const [customCoords, setCustomCoords] = useState(false);
  const [latitude, setLatitude] = useState(SEEDED_TOWNS[0].lat);
  const [longitude, setLongitude] = useState(SEEDED_TOWNS[0].lng);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successToast, setSuccessToast] = useState(false);

  const handleTownChange = (townName: string) => {
    setSelectedTown(townName);
    const town = SEEDED_TOWNS.find((t) => t.name === townName);
    if (town && !customCoords) {
      setLatitude(town.lat);
      setLongitude(town.lng);
    }
  };

  const toggleCrop = (cropId: string) => {
    setSelectedCrops((prev) =>
      prev.includes(cropId)
        ? prev.filter((c) => c !== cropId)
        : [...prev, cropId]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!businessName.trim()) {
      setError('Please enter the Business Name.');
      return;
    }

    if (!phoneNumber.trim()) {
      setError('Please enter a valid Phone Number.');
      return;
    }

    if (selectedCrops.length === 0) {
      setError('Please select at least one accepted crop.');
      return;
    }

    try {
      setLoading(true);

      const payload: RetailerCreateInput = {
        business_name: businessName.trim(),
        owner_name: ownerName.trim() || undefined,
        phone_number: phoneNumber.trim(),
        location_name: selectedTown,
        latitude: Number(latitude),
        longitude: Number(longitude),
        accepted_crops: selectedCrops,
        is_active: true,
      };

      await api.createRetailer(payload);

      setSuccessToast(true);
      setTimeout(() => {
        router.push('/dashboard');
      }, 1500);
    } catch (err: any) {
      setError(err.message || 'Failed to register retailer.');
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto py-4 sm:py-8 space-y-6">
      {/* Back button */}
      <Link
        href="/dashboard"
        className="inline-flex items-center gap-2 text-xs font-semibold text-stone-600 hover:text-agri-700 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        <span>Back to Dashboard</span>
      </Link>

      {/* Success Toast banner */}
      {successToast && (
        <div className="p-4 rounded-2xl bg-emerald-600 text-white shadow-lg flex items-center justify-between animate-bounce">
          <div className="flex items-center gap-2">
            <Check className="w-5 h-5" />
            <span className="text-sm font-bold">
              Retailer registered successfully! Redirecting to dashboard...
            </span>
          </div>
        </div>
      )}

      {/* Main Registration Card */}
      <div className="bg-white rounded-3xl p-6 sm:p-10 border border-stone-200 shadow-sm space-y-8">
        {/* Title Header */}
        <div className="border-b border-stone-100 pb-6">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-agri-100 text-agri-800 text-xs font-bold mb-3">
            <Sparkles className="w-3.5 h-3.5 text-ochre-600" />
            <span>Buyer Onboarding</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-stone-900 tracking-tight">
            Register Wholesale Retailer
          </h1>
          <p className="text-xs sm:text-sm text-stone-500 mt-1.5">
            Add a produce buyer to the Ulavu network. Registered retailers automatically receive incoming farmer leads within 25km via SMS.
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs sm:text-sm flex items-start gap-3">
            <AlertCircle className="w-5 h-5 shrink-0 text-rose-500 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Business Name */}
          <div className="space-y-2">
            <label className="block text-xs font-bold text-stone-700 uppercase tracking-wider">
              Business / Mandi Name <span className="text-rose-500">*</span>
            </label>
            <div className="relative">
              <Store className="w-4 h-4 text-stone-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                required
                placeholder="e.g. Sri Murugan Agro Traders"
                value={businessName}
                onChange={(e) => setBusinessName(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 rounded-xl text-sm border border-stone-200 focus:outline-none focus:ring-2 focus:ring-agri-500 focus:border-transparent bg-stone-50"
              />
            </div>
          </div>

          {/* Owner Name */}
          <div className="space-y-2">
            <label className="block text-xs font-bold text-stone-700 uppercase tracking-wider">
              Owner / Contact Person
            </label>
            <div className="relative">
              <User className="w-4 h-4 text-stone-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="e.g. K. Murugesan"
                value={ownerName}
                onChange={(e) => setOwnerName(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 rounded-xl text-sm border border-stone-200 focus:outline-none focus:ring-2 focus:ring-agri-500 focus:border-transparent bg-stone-50"
              />
            </div>
          </div>

          {/* Phone Number */}
          <div className="space-y-2">
            <label className="block text-xs font-bold text-stone-700 uppercase tracking-wider">
              Phone Number (For Lead SMS &amp; Farmer Contact) <span className="text-rose-500">*</span>
            </label>
            <div className="relative">
              <Phone className="w-4 h-4 text-stone-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="tel"
                required
                placeholder="+919876543210"
                value={phoneNumber}
                onChange={(e) => setPhoneNumber(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 rounded-xl text-sm font-mono border border-stone-200 focus:outline-none focus:ring-2 focus:ring-agri-500 focus:border-transparent bg-stone-50"
              />
            </div>
            <p className="text-[11px] text-stone-400 flex items-center gap-1">
              <Info className="w-3.5 h-3.5 text-stone-400" />
              For live SMS testing, use an Exotel-verified mobile number.
            </p>
          </div>

          {/* Location Dropdown */}
          <div className="space-y-2">
            <label className="block text-xs font-bold text-stone-700 uppercase tracking-wider">
              Location / Mandi Hub <span className="text-rose-500">*</span>
            </label>
            <div className="relative">
              <MapPin className="w-4 h-4 text-stone-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              <select
                value={selectedTown}
                onChange={(e) => handleTownChange(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 rounded-xl text-sm border border-stone-200 focus:outline-none focus:ring-2 focus:ring-agri-500 focus:border-transparent bg-stone-50 appearance-none font-medium text-stone-800"
              >
                {SEEDED_TOWNS.map((town) => (
                  <option key={town.name} value={town.name}>
                    {town.name} ({town.district})
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center justify-between text-[11px] text-stone-500 pt-1">
              <span>Coordinates: {latitude}, {longitude}</span>
              <button
                type="button"
                onClick={() => setCustomCoords(!customCoords)}
                className="text-agri-700 font-semibold hover:underline"
              >
                {customCoords ? 'Use Town Default' : 'Custom Lat/Lng'}
              </button>
            </div>
          </div>

          {/* Custom Lat / Lng inputs (if toggled) */}
          {customCoords && (
            <div className="grid grid-cols-2 gap-4 p-4 rounded-xl bg-stone-50 border border-stone-200">
              <div>
                <label className="block text-[11px] font-bold text-stone-600 uppercase">Latitude</label>
                <input
                  type="number"
                  step="any"
                  value={latitude}
                  onChange={(e) => setLatitude(parseFloat(e.target.value))}
                  className="w-full px-3 py-1.5 rounded-lg text-sm border border-stone-300 font-mono mt-1"
                />
              </div>
              <div>
                <label className="block text-[11px] font-bold text-stone-600 uppercase">Longitude</label>
                <input
                  type="number"
                  step="any"
                  value={longitude}
                  onChange={(e) => setLongitude(parseFloat(e.target.value))}
                  className="w-full px-3 py-1.5 rounded-lg text-sm border border-stone-300 font-mono mt-1"
                />
              </div>
            </div>
          )}

          {/* Accepted Crops Multi-Select Chips */}
          <div className="space-y-3 pt-2">
            <label className="block text-xs font-bold text-stone-700 uppercase tracking-wider">
              Accepted Produce / Crops (Multi-Select) <span className="text-rose-500">*</span>
            </label>
            <div className="flex flex-wrap gap-2.5">
              {AVAILABLE_CROPS.map((crop) => {
                const isSelected = selectedCrops.includes(crop.id);
                return (
                  <button
                    key={crop.id}
                    type="button"
                    onClick={() => toggleCrop(crop.id)}
                    className={`inline-flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs sm:text-sm font-semibold transition-all border ${
                      isSelected
                        ? 'bg-agri-500 text-white border-agri-600 shadow-sm shadow-agri-600/30'
                        : 'bg-stone-50 hover:bg-stone-100 text-stone-700 border-stone-200'
                    }`}
                  >
                    <span>{crop.emoji}</span>
                    <span>{crop.name}</span>
                    <span className={`text-[11px] ${isSelected ? 'text-ochre-300' : 'text-stone-400'}`}>
                      ({crop.tamil})
                    </span>
                    {isSelected && <Check className="w-3.5 h-3.5 ml-1" />}
                  </button>
                );
              })}
            </div>
            <p className="text-[11px] text-stone-400">
              When a farmer mentions any of these crops in Tamil or English during their call, this retailer is eligible for proximity matching.
            </p>
          </div>

          {/* Submit Button */}
          <div className="pt-4">
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-6 rounded-2xl bg-agri-600 hover:bg-agri-700 text-white font-bold text-sm sm:text-base shadow-md shadow-agri-800/20 transition-all transform active:scale-95 disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <span className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin"></span>
                  <span>Saving Retailer...</span>
                </>
              ) : (
                <>
                  <Check className="w-4 h-4" />
                  <span>Register Retailer to Network</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
