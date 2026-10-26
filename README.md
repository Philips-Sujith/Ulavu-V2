# ULAVU (உழவு) — Exotel Voice IVR & SMS Agricultural Lead-Routing System

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js 14](https://img.shields.io/badge/Next.js-14.2-black?style=flat&logo=next.js&logoColor=white)](https://nextjs.org)
[![PostGIS](https://img.shields.io/badge/PostGIS-Enabled-336791?style=flat&logo=postgresql&logoColor=white)](https://postgis.net)
[![Exotel](https://img.shields.io/badge/Exotel-Voice%20IVR%20%26%20SMS-0080FF?style=flat&logo=phone&logoColor=white)](https://exotel.com)

**ULAVU (உழவு)** is a live, production-ready agricultural lead-routing system connecting farmers in Tamil Nadu with wholesale produce buyers and retail mandis in real time via **Exotel inbound telephone IVR**.

Farmers call an Exotel virtual number, hear spoken prompts in natural Tamil (`ta-IN`), and select their crop and farm location using telephone keypad (DTMF 1–9) input. ULAVU's PostGIS spatial query engine computes proximity matches within a 25–35 km radius and announces nearby active buyers as **“Shop 1” (கடை ஒன்று), “Shop 2” (கடை இரண்டு)**, etc., reading their contact phone numbers slowly digit-by-digit with 500ms pauses between digits. The call terminates without connecting the caller directly to retailers, and instant notifications are dispatched via SMS.

Wholesale retailers manage their network, toggle active/paused status, and review incoming farmer leads with action buttons ("Mark as Sold", "Not Interested") through the **Next.js 14 Retailer Portal**.

---

## System Architecture

```
                                      [ FARMER ]
                                           │
                                  1. Phone Call (Inbound)
                                           ▼
                                 [ Exotel ExoPhone ]
                                           │
                    ┌──────────────────────┴──────────────────────┐
                    │                                             │
      [ Exotel Voicebot Stream ]                      [ Exotel Passthru Webhook ]
        wss://<domain>/voice/exotel/ws                POST /voice/exotel
                    │                                             │
                    └──────────────────────┬──────────────────────┘
                                           ▼
                                [ FastAPI Async Backend ]
                                           │
                             PostGIS ST_DWithin (<25-35km)
                                           ▼
                              [ PostgreSQL + PostGIS ]
                                (retailers & inquiries)
                                           │
                       ┌───────────────────┴───────────────────┐
                       ▼                                       ▼
          [ Multi-Shop Voice Readout ]                [ Exotel SMS Dispatch ]
          • "Shop 1: <Name>, <Phone>"                 • Farmer: Buyer details
          • "Shop 2: <Name>, <Phone>"                 • Retailer: Supply alert
          • Slow digit pauses (500ms)                 • Clean exception handling
          • Does NOT connect call to retailer
                                           │
                                           ▼
                            [ Next.js 14 Retailer Portal ]
                            • Real-time KPI Stats Strip
                            • Retailer Cards with Active/Pause Switch
                            • Expandable Incoming Leads
                            • "Mark as Sold" / "Not Interested" actions
```

---

## IVR Keypad Menus (DTMF 1–9)

### 1. Crop Selection Menu
| Key | Crop (Tamil) | Crop (Slug) |
| :---: | :--- | :--- |
| **1** | வெங்காயம் | onion |
| **2** | தக்காளி | tomato |
| **3** | உருளைக்கிழங்கு | potato |
| **4** | கத்தரிக்காய் | brinjal |
| **5** | கேரட் | carrot |
| **6** | முட்டைக்கோஸ் | cabbage |
| **7** | காலிஃப்ளவர் | cauliflower |
| **8** | வெண்டைக்காய் | okra |
| **9** | பச்சை மிளகாய் | chilli |

### 2. Location Selection Menu
| Key | Location (Tamil) | Location (Name) | Coordinates (Lat, Lng) |
| :---: | :--- | :--- | :--- |
| **1** | மதுராந்தகம் | Madurantakam | 12.5085, 79.8850 |
| **2** | செங்கல்பட்டு | Chengalpattu | 12.6841, 79.9836 |
| **3** | காஞ்சிபுரம் | Kanchipuram | 12.8342, 79.7036 |
| **4** | திருக்கழுக்குன்றம் | Tirukalukundram | 12.6105, 80.0537 |
| **5** | உத்திரமேரூர் | Uthiramerur | 12.6152, 79.7570 |
| **6** | அச்சரப்பாக்கம் | Acharapakkam | 12.4419, 79.8174 |
| **7** | செய்யூர் | Cheyyur | 12.3524, 80.0041 |
| **8** | ஸ்ரீபெரும்புதூர் | Sriperumbudur | 12.9675, 79.9427 |
| **9** | வாலாஜாபாத் | Walajabad | 12.7937, 79.8169 |

---

## Step-by-Step Running Guide

### 1. Backend Setup & Running

Open a terminal and navigate to `backend/`:

```powershell
cd "y:\Projects\ULAVU V2\backend"
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

- **Backend API**: `http://localhost:8000`
- **Swagger Docs**: `http://localhost:8000/docs`

### 2. Frontend Portal Setup & Running

Open a new terminal and navigate to `frontend/`:

```powershell
cd "y:\Projects\ULAVU V2\frontend"
npm install
npm run dev
```

- **Retailer Portal**: `http://localhost:3000`
- **Dashboard**: `http://localhost:3000/dashboard`
- **Register Retailer**: `http://localhost:3000/register`

---

## Running Automated Tests

Run backend tests using PowerShell:

```powershell
cd "y:\Projects\ULAVU V2\backend"
$env:PYTHONPATH="."

# 1. Comprehensive Exotel IVR flow (Multi-matches, No-matches, Invalid input, Proximity ranking)
.\venv\Scripts\python.exe tests/test_exotel_ivr_complete.py

# 2. Keypad DTMF mappings, location coordinates & distance tests
.\venv\Scripts\python.exe tests/test_flow.py

# 3. REST API & Exotel passthru webhook endpoint tests
.\venv\Scripts\python.exe tests/test_api.py

# 4. Exotel WebSocket raw s16le PCM streaming & timing tests
.\venv\Scripts\python.exe tests/test_voicebot_ws.py

# 5. Slow phone number digit-by-digit Tamil voice tests
.\venv\Scripts\python.exe tests/test_slow_phone_voice.py

# 6. Exotel SMS construction & trial dispatch test
.\venv\Scripts\python.exe tests/test_sms_demo.py
```

---

## Exotel Dashboard Setup & Configuration

To connect live inbound phone calls from your Exotel phone number to your ULAVU server:

1. **Expose Local Server via ngrok** (for local development):
   ```powershell
   ngrok http 8000
   ```
   Note your public forwarding URL: `https://<subdomain>.ngrok-free.app`

2. **Log in to Exotel Console**:
   Visit [https://my.exotel.com](https://my.exotel.com) and navigate to **App Bazaar / Call Flow Builder**.

3. **Call Flow Configuration**:
   - **Option A (Voicebot Applet — Recommended)**:
     - Add a **Voicebot Applet** to the inbound flow.
     - Set WebSocket URL to: `wss://<your-ngrok-subdomain>.ngrok-free.app/voice/exotel/ws`
     - The bot handles real-time audio playback, DTMF keypad capture, shop announcement, and hangup.
   - **Option B (Gather + Passthru Applet)**:
     - Add a **Gather Applet** for Crop (DTMF 1-9) -> **Passthru Applet** to `https://<your-ngrok-subdomain>.ngrok-free.app/voice/exotel`.
     - Add a **Gather Applet** for Location (DTMF 1-9) -> **Passthru Applet** to `https://<your-ngrok-subdomain>.ngrok-free.app/voice/exotel`.

4. **Assign Flow to ExoPhone**:
   Under **ExoPhones / Virtual Numbers**, assign the inbound call flow to your purchased Exotel number.

> [!NOTE]
> Under Indian TRAI telecom regulations, commercial SMS dispatch via Exotel requires business KYC approval and DLT registration. If an account has not completed KYC, SMS dispatch returns HTTP 403 `RestException: Your account is not yet KYC compliant (Code: 340030)`. ULAVU catches and logs this safely without crashing or interrupting the call flow.
