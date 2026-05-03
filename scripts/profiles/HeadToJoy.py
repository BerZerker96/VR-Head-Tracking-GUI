from ofisare.vr_headjoy import HeadJoystickDirection
#****************************************************************
# Head -> Gamepad right-stick (Forza / sim-style), tuned for a
# mouse-like, immediate-response feel.
#
# === HOW TO TOGGLE FEATURES ===
# Comment a line out (prefix with #) in the TOGGLEABLE SETTINGS
# block below to disable that feature. When disabled, a safe
# default of 0 is used (effectively switching the feature off).
# The GUI configurator does this for you automatically.
#
# Tunable params (all controlled via the GUI):
#   deadzone   - head rotation below this angle is ignored
#                (suppresses tremor; comment line to disable)
#   exponent   - response curve; 0 = linear, >1 = softer near
#                center (comment line to disable)
#   maxAngle   - head rotation that produces full stick
#                deflection (LOWER = MORE responsive)
#   scale      - output multiplier (1.0 = full)
#
# NOTE: Forza only uses yaw, but pitch is kept symmetric for
# other titles that consume both axes.
#****************************************************************

vrToGamepad.setController(VigemController.XBoxController)

# === TOGGLEABLE SETTINGS ===
# Comment a line below (with #) to disable that feature.
deadzone = 0
# exponent = 0

# === FIXED SETTINGS ===
maxAngle = 85
scale    = 1.5

# Fallback defaults if a toggleable line above is commented out.
# (Leave this block alone -- it makes the # toggles work.)
try: deadzone
except NameError: deadzone = 0
try: exponent
except NameError: exponent = 0

# Yaw (left/right head turn) -- primary look axis
vrToGamepad.headJoy.left  = HeadJoystickDirection(True,  deadzone, maxAngle, exponent, scale)
vrToGamepad.headJoy.right = HeadJoystickDirection(False, deadzone, maxAngle, exponent, scale)

# Pitch (up/down head tilt) -- ignored by Forza, used by other games
vrToGamepad.headJoy.down  = HeadJoystickDirection(True,  deadzone, maxAngle, exponent, scale)
vrToGamepad.headJoy.up    = HeadJoystickDirection(False, deadzone, maxAngle, exponent, scale)

vrToGamepad.headMode.current = 1
