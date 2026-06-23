import threading


class SimState:
    def __init__(self, gates, start_pos=(0.0, 2.0, 0.0), start_yaw=0.0):
        self.lock = threading.Lock()
        self.start_pos = list(start_pos)
        self.start_yaw = start_yaw
        self.gates = gates

        self.pos = list(start_pos)
        self.vel = [0.0, 0.0, 0.0]
        self.yaw = start_yaw
        self.yaw_vel = 0.0

        self.target_pos = list(start_pos)
        self.target_yaw = start_yaw

        self.crashed = False
        self.crash_time = None
        self.crash_count = 0
        self.alive = True

        self.frame_bytes = b""

    def snapshot_status(self):
        with self.lock:
            return {
                "position": {"x": self.pos[0], "y": self.pos[1], "z": self.pos[2]},
                "yaw": self.yaw,
                "crashed": self.crashed,
                "alive": self.alive,
                "crash_count": self.crash_count,
            }

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
            self.yaw = self.start_yaw
            self.yaw_vel = 0.0
            self.target_pos = list(self.start_pos)
            self.target_yaw = self.start_yaw
            self.crashed = False
            self.crash_time = None
            self.alive = True

    def set_frame_bytes(self, data):
        with self.lock:
            self.frame_bytes = data

    def get_frame_bytes(self):
        with self.lock:
            return self.frame_bytes
