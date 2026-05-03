# mode to switch between w (run forward) and s (slowly walk forward)
running = Mode()
running.current = 1

drone = Mode()

# headset turning
vrRoomscale.yaw.negativeAction = KeyPress(Key.A)
vrRoomscale.yaw.positiveAction = KeyPress(Key.D)

vrRoomscale.pitch.sensitivity = 0.3
vrRoomscale.yaw.sensitivity = 0.3
vrRoomscale.pitch.centerEpsilon = 0.1
vrRoomscale.pitch.negativeAction = KeyPress(Key.V)
vrRoomscale.pitch.positiveAction = KeyPress(Key.R)
