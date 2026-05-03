# ============================================================================
#  VRCompanion -> OpenTrack UDP head-tracking sender
#  For: itsloopyo/resident-evil-requiem-headtracking
#
#  Wire format VERIFIED from opentrack-tracker-udp.dll disassembly:
#    48 bytes = 6 little-endian Float64 in order:
#      x, y, z   (cm)
#      yaw, pitch, roll  (degrees)
#
#  Recenter mid-game with the mod's Home / Ctrl+Shift+T hotkey.
# ============================================================================


# ============================================================================
#  CONFIGURATION
# ============================================================================

# ----- Network -------------------------------------------------------------
IP_ADDRESS = "127.0.0.1"
PORT       = 4242

# ----- Sensitivity (how much your motion is amplified before sending) -----
# 1.0 = 1:1 with your real head movement
# >1.0 = exaggerated movement (e.g. 1.5 = 50% bigger)
# <1.0 = damped movement
# Tip: you can ALSO tune in the mod's HeadTracking.ini via SensitivityX/Y/Z
# and YawMultiplier/PitchMultiplier/RollMultiplier. Pick one place; mixing
# both can compound and feel weird.
YAW_GAIN   = 1
PITCH_GAIN = 1
ROLL_GAIN  = 1
X_GAIN     = 1
Y_GAIN     = 1
Z_GAIN     = 1
# ----- Axis inversion (set True to flip a direction) ----------------------
# Defaults below are calibrated for the typical OpenVR-on-VRCompanion case
# where pitch, roll, and Y come in opposite to what OpenTrack expects.
# If any axis still goes the wrong way, flip its INVERT_* value.
INVERT_YAW   = False
INVERT_PITCH = True    # looking up should send positive pitch -> camera up
INVERT_ROLL  = True    # tilting head right should tilt world right
INVERT_X     = False
INVERT_Y     = True    # standing up should send positive Y
INVERT_Z     = False

# ----- Reference / units --------------------------------------------------
RECENTER_DELAY_SEC = 2
ROTATION_UNITS     = "auto"   # "auto" | "rad" | "deg"

# ----- Logging ------------------------------------------------------------
HEARTBEAT_SEC = 2.0


# ============================================================================
#  SCRIPT
# ============================================================================

import time
import System
from System.Net import IPEndPoint, IPAddress
from System.Net.Sockets import UdpClient

if starting:
    environment.headTracker = type('HT', (object,), {})()
    ht = environment.headTracker

    ht.udp     = UdpClient()
    ht.target  = IPEndPoint(IPAddress.Parse(IP_ADDRESS), PORT)
    ht.buf     = System.Array.CreateInstance(System.Byte, 48)
    ht.sent    = 0
    ht.lastLog = 0.0

    ht.refYaw, ht.refPitch, ht.refRoll = 0.0, 0.0, 0.0
    ht.refX, ht.refY, ht.refZ = 0.0, 0.0, 0.0
    ht.refCaptured = False
    ht.startTime = time.clock()
    ht.recenterDelay = RECENTER_DELAY_SEC
    ht.heartbeat = HEARTBEAT_SEC

    # Combine gain and invert into single signed multipliers so the hot path
    # is one multiply per axis.
    ht.yawMul   = (-1.0 if INVERT_YAW   else 1.0) * YAW_GAIN
    ht.pitchMul = (-1.0 if INVERT_PITCH else 1.0) * PITCH_GAIN
    ht.rollMul  = (-1.0 if INVERT_ROLL  else 1.0) * ROLL_GAIN
    ht.xMul     = (-1.0 if INVERT_X     else 1.0) * X_GAIN
    ht.yMul     = (-1.0 if INVERT_Y     else 1.0) * Y_GAIN
    ht.zMul     = (-1.0 if INVERT_Z     else 1.0) * Z_GAIN

    ht.peakYaw = 0.0; ht.peakPitch = 0.0; ht.peakRoll = 0.0
    ht.peakX   = 0.0; ht.peakY     = 0.0; ht.peakZ    = 0.0

    if ROTATION_UNITS == "rad":
        ht.radians, ht.detected = True, True
    elif ROTATION_UNITS == "deg":
        ht.radians, ht.detected = False, True
    else:
        ht.radians, ht.detected = False, False

    def _on_vr_update():
        try:
            ht = environment.headTracker
            h  = vr.headPose
            if h is None:
                return

            yaw_raw   = float(h.yaw)
            pitch_raw = float(h.pitch)
            roll_raw  = float(h.roll)

            if not ht.detected:
                biggest = max(abs(yaw_raw), abs(pitch_raw), abs(roll_raw))
                if biggest > 3.5:
                    ht.radians = False
                    ht.detected = True
                    diagnostics.debug("[6DOF] auto-detect: degrees")
                elif biggest > 0.5:
                    ht.radians = True
                    ht.detected = True
                    diagnostics.debug("[6DOF] auto-detect: radians")

            if ht.radians:
                yaw_deg   = yaw_raw   * 57.2957795130823
                pitch_deg = pitch_raw * 57.2957795130823
                roll_deg  = roll_raw  * 57.2957795130823
            else:
                yaw_deg, pitch_deg, roll_deg = yaw_raw, pitch_raw, roll_raw

            now = time.clock()

            if not ht.refCaptured and (now - ht.startTime) >= ht.recenterDelay:
                ht.refYaw   = yaw_deg
                ht.refPitch = pitch_deg
                ht.refRoll  = roll_deg
                ht.refX     = float(h.position.x)
                ht.refY     = float(h.position.y)
                ht.refZ     = float(h.position.z)
                ht.refCaptured = True
                diagnostics.debug("[6DOF] reference captured")

            x_cm = 0.0; y_cm = 0.0; z_cm = 0.0
            yaw_out = 0.0; pitch_out = 0.0; roll_out = 0.0

            if ht.refCaptured:
                d_yaw   = yaw_deg   - ht.refYaw
                d_pitch = pitch_deg - ht.refPitch
                d_roll  = roll_deg  - ht.refRoll

                if d_yaw > 180.0:
                    d_yaw -= 360.0
                elif d_yaw < -180.0:
                    d_yaw += 360.0

                yaw_out   = d_yaw   * ht.yawMul
                pitch_out = d_pitch * ht.pitchMul
                roll_out  = d_roll  * ht.rollMul

                x_cm = (float(h.position.x) - ht.refX) * 100.0 * ht.xMul
                y_cm = (float(h.position.y) - ht.refY) * 100.0 * ht.yMul
                z_cm = (float(h.position.z) - ht.refZ) * 100.0 * ht.zMul

                if abs(yaw_out)   > abs(ht.peakYaw):   ht.peakYaw   = yaw_out
                if abs(pitch_out) > abs(ht.peakPitch): ht.peakPitch = pitch_out
                if abs(roll_out)  > abs(ht.peakRoll):  ht.peakRoll  = roll_out
                if abs(x_cm)      > abs(ht.peakX):     ht.peakX     = x_cm
                if abs(y_cm)      > abs(ht.peakY):     ht.peakY     = y_cm
                if abs(z_cm)      > abs(ht.peakZ):     ht.peakZ     = z_cm

            # OpenTrack wire order: x, y, z, yaw, pitch, roll
            gb  = System.BitConverter.GetBytes
            bc  = System.Buffer.BlockCopy
            buf = ht.buf
            bc(gb(x_cm),      0, buf,  0, 8)
            bc(gb(y_cm),      0, buf,  8, 8)
            bc(gb(z_cm),      0, buf, 16, 8)
            bc(gb(yaw_out),   0, buf, 24, 8)
            bc(gb(pitch_out), 0, buf, 32, 8)
            bc(gb(roll_out),  0, buf, 40, 8)

            ht.udp.Send(buf, 48, ht.target)
            ht.sent += 1

            if ht.heartbeat > 0 and (now - ht.lastLog) >= ht.heartbeat:
                ht.lastLog = now
                diagnostics.debug("[6DOF] peaks  x=" + str(round(ht.peakX, 1)) +
                                  " y=" + str(round(ht.peakY, 1)) +
                                  " z=" + str(round(ht.peakZ, 1)) +
                                  "  yaw=" + str(round(ht.peakYaw, 1)) +
                                  " pitch=" + str(round(ht.peakPitch, 1)) +
                                  " roll=" + str(round(ht.peakRoll, 1)))
                ht.peakYaw = 0.0; ht.peakPitch = 0.0; ht.peakRoll = 0.0
                ht.peakX   = 0.0; ht.peakY     = 0.0; ht.peakZ    = 0.0
        except Exception, e:
            diagnostics.debug("[6DOF] error: " + str(e))

    vr.update += _on_vr_update
    diagnostics.debug("[6DOF] OpenTrack stream -> " + IP_ADDRESS + ":" +
                      str(PORT) + "  (gains active, pitch+roll+y inverted)")
