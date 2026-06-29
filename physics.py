import math
import time

GRAVITY = 4.0
ATTRACT_K = 3.0
DRAG = 2.5
YAW_ATTRACT_K = 6.0
YAW_DRAG = 4.0

# Terminal velocity — keeps the drone feeling like it has mass instead of
# snapping to the commanded target. Tune for a punchier/floatier feel.
MAX_SPEED = 12.0

GROUND_Y = 0.3
CEILING_Y = 14.0
BOUND_X = 20.0

CRASH_FREEZE_SECONDS = 1.5

TWO_PI = 2 * math.pi


def _angle_diff(a, b):
    d = (a - b) % TWO_PI
    if d > math.pi:
        d -= TWO_PI
    return d


def update(state, dt):
    with state.lock:
        if state.crashed:
            if state.crash_time is not None and (time.time() - state.crash_time) >= CRASH_FREEZE_SECONDS:
                _do_reset_locked(state)
            return

        pos = state.pos
        vel = state.vel
        target = state.target_pos
        prev_z = pos[2]

        for i in range(3):
            err = target[i] - pos[i]
            acc = err * ATTRACT_K - vel[i] * DRAG
            if i == 1:
                acc -= GRAVITY
            state.accel[i] = acc
            vel[i] += acc * dt
            pos[i] += vel[i] * dt

        # Clamp to terminal velocity so commands can't fling the drone.
        speed = math.sqrt(vel[0] ** 2 + vel[1] ** 2 + vel[2] ** 2)
        if speed > MAX_SPEED:
            scale = MAX_SPEED / speed
            vel[0] *= scale
            vel[1] *= scale
            vel[2] *= scale

        yaw_err = _angle_diff(state.target_yaw, state.yaw)
        yaw_acc = yaw_err * YAW_ATTRACT_K - state.yaw_vel * YAW_DRAG
        state.yaw_vel += yaw_acc * dt
        state.yaw += state.yaw_vel * dt

        crashed = pos[1] <= GROUND_Y or pos[1] >= CEILING_Y or abs(pos[0]) >= BOUND_X

        if not crashed:
            for gate in state.gates:
                in_opening = abs(pos[0] - gate.x) <= gate.half_w and abs(pos[1] - gate.y) <= gate.half_h
                # Crash: clipped the gate plane while outside the opening.
                if abs(pos[2] - gate.z) <= gate.thickness / 2.0 and not in_opening:
                    crashed = True
                    break
                # Score: crossed the gate plane (forward) through the opening.
                if not gate.passed and prev_z < gate.z <= pos[2] and in_opening:
                    gate.passed = True
                    state.gates_passed += 1

        if crashed:
            state.crashed = True
            state.crash_time = time.time()
            state.crash_count += 1
            state.alive = False


def _do_reset_locked(state):
    state.pos = list(state.start_pos)
    state.vel = [0.0, 0.0, 0.0]
    state.accel = [0.0, 0.0, 0.0]
    state.yaw = state.start_yaw
    state.yaw_vel = 0.0
    state.target_pos = list(state.start_pos)
    state.target_yaw = state.start_yaw
    state.crashed = False
    state.crash_time = None
    state.alive = True
    state.gates_passed = 0
    for gate in state.gates:
        gate.passed = False
    state.start_time = time.time()
