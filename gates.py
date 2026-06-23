import random


class Gate:
    def __init__(self, x, y, z, half_w=2.5, half_h=2.0, thickness=1.0):
        self.x = x
        self.y = y
        self.z = z
        self.half_w = half_w
        self.half_h = half_h
        self.thickness = thickness


def generate_random_gates(n=5, z_spacing=15.0, z_start=15.0):
    gates = []
    for i in range(n):
        z = z_start + i * z_spacing
        x = random.uniform(-4.0, 4.0)
        y = random.uniform(2.0, 5.0)
        gates.append(Gate(x, y, z))
    return gates
