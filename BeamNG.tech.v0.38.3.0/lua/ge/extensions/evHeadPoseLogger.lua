-- evHeadPoseLogger.lua
--
-- *** UNTESTED - never loaded into a running BeamNG.tech instance. ***
-- Written from this session (macOS, no Windows/GPU access - same constraint as
-- D004/D027) by reading the existing codebase only (core_camera API usage
-- confirmed real via lerpCamToKiosk.lua/lerpCamFromKiosk.lua; the polling/
-- queue_lua_command convention confirmed real via evProjectBridge.lua and
-- receive_ui.py's _ui_listener). Has NOT been validated against: correct engine
-- load order, onUpdate actually firing at the expected rate in VR, JSON encoding
-- round-trip through queue_lua_command, or real sim-time/wall-clock drift over a
-- full session. Validate on the real workstation before trusting any data this
-- produces - do not use for real data collection until then.
--
-- Decision.md D031 established: (1) core_camera.getPosition()/getQuat() are
-- confirmed callable from GE Lua (used today in the camera-lerp flowgraph
-- nodes); (2) there is NO existing gaze-logging hook in BeamNG's Lua layer to
-- extend - gaze capture is a wholly separate external application; (3) the
-- going-forward fix should keep head-pose timestamps on the SAME backend
-- wall-clock convention the interaction log already uses (receive_ui.py's
-- _ui_listener stamps `datetime.now()` at message-receipt time), not a BeamNG
-- Lua clock, since that domain is already proven (D020/D026/D045) to compose
-- correctly with the externally-captured gaze stream via simple epoch alignment.
--
-- Design (per D031): this file buffers per-frame samples LOCALLY, tagged with
-- BeamNG's own sim-time delta (for *relative* ordering/spacing within one
-- buffer drain) - it does NOT itself assign a wall-clock timestamp, because
-- GE Lua's own clock is not guaranteed to agree with the Python backend's
-- clock (even on one machine, cross-process clock reads can differ by a few
-- ms) and D031's whole point was to avoid introducing a THIRD clock domain
-- alongside gaze and interactions. Python (receive_ui.py, extending the
-- existing _ui_listener/_odometer_worker polling pattern) is responsible for:
--   1. polling drainBuffer() at a fixed cadence (matching the existing 5 Hz
--      _ui_listener poll is a reasonable starting point - NOT validated as
--      sufficient for fixation-level analysis; that needs the real-hardware
--      calibration-nod check D031 proposed, not an assumption),
--   2. stamping the WHOLE drained batch with one receipt-time wall-clock
--      timestamp (datetime.now(), same convention as interactions_*.csv),
--   3. reconstructing each sample's approximate wall-clock time by walking
--      backward from the batch receipt time using each sample's own
--      recorded `dtSim` (this file's job is only to make that possible, not
--      to do it itself).
--
-- Usage from Python (BeamNGpy), matching evProjectBridge.lua's existing
-- convention exactly:
--   bng.control.queue_lua_command(
--     'return extensions.evHeadPoseLogger.drainBuffer()', response=True)
--   bng.control.queue_lua_command(
--     'extensions.evHeadPoseLogger.markCalibrationNod()')

local M = {}

-- Ring buffer of per-frame samples since the last drain. Each entry:
--   { px, py, pz,           -- core_camera.getPosition(), world space
--     qx, qy, qz, qw,        -- core_camera.getQuat()
--     dtSim,                 -- simulation-time delta since the PREVIOUS
--                             -- sample in this buffer (seconds) - NOT a
--                             -- wall-clock value; see header
--     marker }                -- nil for a normal sample, or a string tag
--                             -- (e.g. "calibration_nod") for a marker event
local buffer = {}

-- Hard cap so a Python-side stall (e.g. a slow poll, a dropped connection)
-- cannot grow this table unbounded and leak memory for the rest of the
-- session - matches the spirit of the existing bridge's bounded queues
-- (evProjectBridge.lua's flowgraphReplyQueue is drained promptly by design;
-- this buffer could NOT be promptly drained if Python falls behind, so it
-- needs an explicit cap, which the bridge's own queues don't need).
local MAX_BUFFER_SAMPLES = 2000

local enabled = false

--- Called every simulation tick while enabled. Captures head pose and appends
--- to the buffer. UNTESTED: whether onUpdate is the right hook (vs. a
--- per-eye-render hook needed for true per-frame-in-VR granularity) has not
--- been checked against BeamNG's actual VR render loop - flagged here rather
--- than assumed, since D020/D021's own gaze-rate findings (~199-200 Hz) are
--- well above typical onUpdate physics-tick rates (BeamNG's physics step is
--- commonly 100 Hz / 0.01s, not whatever the VR compositor renders at) and a
--- mismatch here would under-sample head pose relative to gaze.
--- @param dtReal number Wall-clock delta since last call (engine-provided).
--- @param dtSim number Simulation-time delta since last call (engine-provided).
--- @param dtRaw number Unscaled delta (engine-provided).
M.onUpdate = function(dtReal, dtSim, dtRaw)
  if not enabled then return end

  local ok, pos, rot = pcall(function()
    return core_camera.getPosition(), core_camera.getQuat()
  end)
  if not ok or not pos or not rot then
    -- Do not silently skip-forever on a transient failure, but do not spam
    -- the log every tick either - log once per failure, not per frame.
    log('W', 'evHeadPoseLogger', 'core_camera pose read failed this tick')
    return
  end

  if #buffer >= MAX_BUFFER_SAMPLES then
    -- Drop the OLDEST sample, not the newest - a stalled Python poller should
    -- see recency-biased data once it catches up, not a frozen-old window.
    table.remove(buffer, 1)
    log('W', 'evHeadPoseLogger', 'Buffer at cap (' .. MAX_BUFFER_SAMPLES ..
        '); dropping oldest sample - Python-side poll may be stalled')
  end

  table.insert(buffer, {
    px = pos.x, py = pos.y, pz = pos.z,
    qx = rot.x, qy = rot.y, qz = rot.z, qw = rot.w,
    dtSim = dtSim or 0,
  })
end

--- Enable/disable per-frame capture. Left OFF by default (enabled=false
--- above) so loading this extension never changes existing behaviour until
--- a session deliberately turns it on - same "additive, default-unchanged"
--- convention as D024/D036's condition/backend parameters on the Python side.
--- @param on boolean
M.setEnabled = function(on)
  enabled = (on == true)
  log('I', 'evHeadPoseLogger', 'Capture ' .. (enabled and 'ENABLED' or 'disabled'))
end

--- Insert a distinctive marker sample at the current pose, for the D031
--- calibration-nod protocol: perform one sharp, recognizable head motion on
--- command at the start of a new recording session, logged independently by
--- BOTH this file (via this marker) and the separate gaze-capture
--- application's own log, so the two clock domains' real offset can be
--- measured empirically after the fact rather than assumed.
--- UNTESTED: whether this marker is visually/kinematically distinctive enough
--- to auto-detect in the gaze stream's own head-motion proxy (if it has one)
--- or whether it needs a manual timestamp read-off has not been checked.
M.markCalibrationNod = function()
  local ok, pos, rot = pcall(function()
    return core_camera.getPosition(), core_camera.getQuat()
  end)
  if not ok or not pos or not rot then
    log('E', 'evHeadPoseLogger', 'markCalibrationNod: pose read failed, marker NOT recorded')
    return
  end
  table.insert(buffer, {
    px = pos.x, py = pos.y, pz = pos.z,
    qx = rot.x, qy = rot.y, qz = rot.z, qw = rot.w,
    dtSim = 0,
    marker = 'calibration_nod',
  })
  log('I', 'evHeadPoseLogger', 'Calibration-nod marker recorded')
end

--- Called by Python (queue_lua_command with response=True), matching
--- evProjectBridge.lua's existing poll convention. Returns and clears the
--- buffer as a JSON array string. Python is responsible for assigning a
--- wall-clock timestamp to this whole batch on receipt and, if per-sample
--- resolution is needed, reconstructing each sample's approximate time by
--- walking backward through dtSim - see the file header.
--- @return string JSON-encoded array of buffered samples (possibly empty: "[]").
M.drainBuffer = function()
  local ok, encoded = pcall(function()
    if jsonEncode then return jsonEncode(buffer) end
    if json and json.encode then return json.encode(buffer) end
    return nil
  end)
  if not ok or encoded == nil then
    log('E', 'evHeadPoseLogger', 'drainBuffer: JSON encode failed - returning empty array, samples LOST')
    buffer = {}
    return '[]'
  end
  buffer = {}
  return encoded
end

--- Diagnostic helper (not needed for normal operation) - lets Python confirm
--- the extension loaded and report current buffer depth without draining it,
--- useful for a first smoke-test on the real hardware before trusting any
--- recorded session.
--- @return string JSON object: { enabled: bool, bufferedSamples: number }
M.getStatus = function()
  local status = { enabled = enabled, bufferedSamples = #buffer }
  local ok, encoded = pcall(function()
    if jsonEncode then return jsonEncode(status) end
    if json and json.encode then return json.encode(status) end
    return nil
  end)
  if ok and encoded then return encoded end
  return '{"enabled":' .. tostring(enabled) .. ',"bufferedSamples":' .. tostring(#buffer) .. '}'
end

M.onExtensionLoaded = function()
  log('I', 'evHeadPoseLogger', 'evHeadPoseLogger extension loaded (capture starts disabled - call setEnabled(true)). UNTESTED - see file header before using for real data collection.')
end

return M
