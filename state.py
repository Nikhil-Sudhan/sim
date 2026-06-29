import math
import threading
import time


class SimState:
    def __init__(self, gates, start_pos=(0.0, 2.0, 0.0), start_yaw=0.0):
        self.lock = threading.Lock()
        self.start_pos = list(start_pos)
        self.start_yaw = start_yaw
        self.gates = gates

        self.pos = list(start_pos)
        self.vel = [0.0, 0.0, 0.0]
        self.accel = [0.0, 0.0, 0.0]
        self.yaw = start_yaw
        self.yaw_vel = 0.0

        self.target_pos = list(start_pos)
        self.target_yaw = start_yaw

        self.crashed = False
        self.crash_time = None
        self.crash_count = 0
        self.alive = True

        self.gates_passed = 0
        self.start_time = time.time()

        # Lazy-encode bookkeeping: the render loop only spends time encoding a
        # JPEG when a client has actually asked for /frame recently.
        self.frame_requested_at = 0.0
        self.frame_bytes = b""

    # ── telemetry ──────────────────────────────────────────────────────────
    def _next_gate_locked(self):
        """Nearest gate still ahead of the drone along +z (None if past all)."""
        ahead = [g for g in self.gates if g.z > self.pos[2]]
        if not ahead:
            return None
        return min(ahead, key=lambda g: g.z - self.pos[2])

    def snapshot_status(self):
        with self.lock:
            speed = math.sqrt(sum(v * v for v in self.vel))
            ng = self._next_gate_locked()
            if ng is not None:
                dx, dy, dz = ng.x - self.pos[0], ng.y - self.pos[1], ng.z - self.pos[2]
                next_gate = {
                    "x": ng.x, "y": ng.y, "z": ng.z,
                    "half_w": ng.half_w, "half_h": ng.half_h,
                    "distance": math.sqrt(dx * dx + dy * dy + dz * dz),
                }
            else:
                next_gate = None
            return {
                "position": {"x": self.pos[0], "y": self.pos[1], "z": self.pos[2]},
                "velocity": {"x": self.vel[0], "y": self.vel[1], "z": self.vel[2]},
                "acceleration": {"x": self.accel[0], "y": self.accel[1], "z": self.accel[2]},
                "speed": speed,
                "yaw": self.yaw,
                "yaw_rate": self.yaw_vel,
                "crashed": self.crashed,
                "alive": self.alive,
                "crash_count": self.crash_count,
                "gates_passed": self.gates_passed,
                "gates_total": len(self.gates),
                "next_gate": next_gate,
                "time_alive": time.time() - self.start_time,
            }

    def snapshot_gates(self):
        """Ground-truth gate geometry — lets the vision side validate distance."""
        with self.lock:
            return [
                {
                    "x": g.x, "y": g.y, "z": g.z,
                    "half_w": g.half_w, "half_h": g.half_h,
                    "width": g.half_w * 2.0, "height": g.half_h * 2.0,
                    "thickness": g.thickness,
                }
                for g in self.gates
            ]

    # ── control ────────────────────────────────────────────────────────────
    def set_target(self, x, y, z, yaw):
        with self.lock:
            self.target_pos = [x, y, z]
            self.target_yaw = yaw

    def reset(self, new_gates=None):
        with self.lock:
            if new_gates is not None:
                self.gates = new_gates
            self.pos = list(self.start_pos)
            self.vel = [0.0, 0.0, 0.0]
            self.accel = [0.0, 0.0, 0.0]
            self.yaw = self.start_yaw
            self.yaw_vel = 0.0
            self.target_pos = list(self.start_pos)
            self.target_yaw = self.start_yaw
            self.crashed = False
            self.crash_time = None
            self.alive = True
            self.gates_passed = 0
            self.start_time = time.time()

    # ── frame plumbing ─────────────────────────────────────────────────────
    def note_frame_request(self):
        with self.lock:
            self.frame_requested_at = time.monotonic()

    def client_wants_frame(self, now, window=2.0):
        with self.lock:
            return (now - self.frame_requested_at) < window

    def set_frame_bytes(self, data):
        with self.lock:
            self.frame_bytes = data

    def get_frame_bytes(self):
        with self.lock:
            return self.frame_bytes
