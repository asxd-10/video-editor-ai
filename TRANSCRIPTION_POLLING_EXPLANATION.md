# Transcription Polling Explanation

## 🔍 Why So Much Polling?

### **Current Polling Sources:**

1. **VideoView Component** (Main polling)
   - **Trigger:** When `transcriptStatus === 'queued'`
   - **Frequency:** Every 5 seconds
   - **Purpose:** Check if transcription is complete
   - **Location:** `frontend/src/pages/VideoView.jsx` line 37-45

2. **EditJobManager Component** (Duplicate polling - FIXED)
   - **Trigger:** On mount and every 5 seconds
   - **Frequency:** Every 5 seconds continuously
   - **Purpose:** Check if transcript exists (for enabling features)
   - **Problem:** This was causing duplicate requests
   - **Fix:** Removed continuous polling, only checks once on mount

### **Why Polling Happens:**

The API endpoint `/transcript/status` only returns:
- `"complete"` - Transcript exists in database
- `"not_found"` - Transcript doesn't exist

**It doesn't track "queued" status** - that's only in the frontend state.

So when you click "Transcribe":
1. Frontend sets `transcriptStatus = 'queued'` (optimistic update)
2. API queues Celery task (background)
3. Frontend polls every 5 seconds to check if transcript exists
4. Once transcript is saved to DB, status changes to `"complete"`

---

## 🐛 Issues Found & Fixed

### **Issue 1: Status Not Updating Immediately**
**Problem:** When clicking "Transcribe", status stayed as "Not started"
**Root Cause:** `loadTranscriptStatus()` was overwriting 'queued' with 'not_found'
**Fix:** Modified `loadTranscriptStatus()` to preserve 'queued' status until 'complete'

### **Issue 2: Button Still Enabled**
**Problem:** Button wasn't disabled when status was 'queued'
**Fix:** Button now shows spinner and "Processing..." when `transcriptStatus === 'queued'`

### **Issue 3: Excessive Polling**
**Problem:** `EditJobManager` was polling every 5 seconds continuously
**Fix:** Removed continuous polling from `EditJobManager` - only checks once on mount

### **Issue 4: No Tooltip**
**Problem:** No indication of what service is used
**Fix:** Added hover tooltip: "Transcribed by Whisper AI (faster-whisper)"

---

## 📊 Polling Frequency

### **Before Fix:**
- VideoView: Every 5 seconds (when queued)
- EditJobManager: Every 5 seconds (always)
- **Total:** ~12 requests per minute (duplicate)

### **After Fix:**
- VideoView: Every 5 seconds (only when queued)
- EditJobManager: Once on mount (no continuous polling)
- **Total:** ~12 requests per minute (single source)

### **When Polling Stops:**
- When `transcriptStatus === 'complete'` → Polling stops
- When component unmounts → Polling stops
- After 5 minutes (safety timeout) → Polling stops

---

## 🎯 Ideal Workflow (After Fixes)

1. **User clicks "Transcribe"**
   - Button shows spinner immediately
   - Status changes to "Processing with Whisper AI..."
   - Button disabled

2. **Background task starts**
   - Celery queues transcription task
   - Frontend polls every 5 seconds

3. **Polling behavior**
   - First check: After 2 seconds (quick check)
   - Then: Every 5 seconds
   - Stops when: Status becomes 'complete'

4. **Transcription completes**
   - Status changes to "Complete"
   - "Done" badge appears with tooltip
   - Transcript viewer appears
   - Features enabled (jump cuts, captions)

---

## 💡 Why Polling is Necessary

**Alternative approaches considered:**
1. **WebSockets:** Real-time updates (complex, requires WebSocket server)
2. **Server-Sent Events (SSE):** One-way updates (simpler, but still requires server changes)
3. **Long polling:** Keep connection open (inefficient)
4. **Polling:** Simple, works with current architecture ✅

**For MVP:** Polling is fine - it's simple and works reliably.

**Future improvement:** Could add WebSocket support for real-time updates, but not needed for hackathon.

