Constants for WASD keys
KEY_W = Key.W
KEY_A = Key.A
KEY_S = Key.S
KEY_D = Key.D

def afterUpdate(sender):
    # Required globals from your hDirection class and initialization
    global bMouseLookXEnabled
    global bMouseLookYEnabled
    global LEFT_DIRECTION 
    global RIGHT_DIRECTION
    global UP_DIRECTION
    global DOWN_DIRECTION 

--- X Axis (Yaw) -> Mapping to A and D ---
Get current head rotation
    yaw = environment.vr.headPose.yaw
Map degrees to the value range defined in your hDirection objects
    headX = filters.ensureMapRange(yaw, LEFT_DIRECTION.maxDegrees, RIGHT_DIRECTION.maxDegrees, LEFT_DIRECTION.maxValue, RIGHT_DIRECTION.maxValue)

Check if head is turned left/right past the deadzone
    isLeft = headX < -LEFT_DIRECTION.deadZone
    isRight = headX > RIGHT_DIRECTION.deadZone

keyboard.setKey(key, True) holds the key; (key, False) releases it
    keyboard.setKey(KEY_A, isLeft)
    keyboard.setKey(KEY_D, isRight)

--- Y Axis (Pitch) -> Mapping to W and S ---
    pitch = environment.vr.headPose.pitch
    headY = filters.ensureMapRange(pitch, UP_DIRECTION.maxDegrees, DOWN_DIRECTION.maxDegrees, UP_DIRECTION.maxValue, DOWN_DIRECTION.maxValue)

Check if head is tilted up/down past the deadzone
    isUp = headY < -UP_DIRECTION.deadZone
    isDown = headY > DOWN_DIRECTION.deadZone

    keyboard.setKey(KEY_W, isUp)
    keyboard.setKey(KEY_S, isDown)

    # 3. --- Diagnostics (Visible in FreePIE/VRCompanion window) ---
    diagnostics.watch(headX, "Horizontal Position")
    diagnostics.watch(headY, "Vertical Position")
    diagnostics.watch(isUp, "Pressing W (Forward)")
    diagnostics.watch(isDown, "Pressing S (Backward)")
