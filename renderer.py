import io
import math

import pygame

WIDTH, HEIGHT = 640, 480
FOV_DEG = 90.0
NEAR_CLIP = 0.3

# Pinhole focal length in pixels for the rendered camera. The vision client
# uses this (via /gates) to turn an apparent gate width into a real distance.
FOCAL_PX = (WIDTH / 2.0) / math.tan(math.radians(FOV_DEG) / 2.0)

SKY_TOP = (110, 170, 230)
SKY_HORIZON = (190, 220, 240)
GROUND_NEAR = (60, 130, 60)
GROUND_FAR = (110, 170, 110)

GATE_COLOR = (255, 140, 0)
GATE_EDGE_COLOR = (120, 60, 0)
GATE_BAR_RATIO = 0.35

HUD_COLOR = (255, 255, 255)
CRASH_COLOR = (220, 40, 40)

RESET_BUTTON_RECT = pygame.Rect(WIDTH - 110, 10, 100, 36)


def _build_background():
    """Pre-render the static sky/ground gradient once (not per frame)."""
    surf = pygame.Surface((WIDTH, HEIGHT))
    half = HEIGHT // 2
    for i in range(half):
        t = i / max(1, half)
        color = [int(SKY_TOP[c] + (SKY_HORIZON[c] - SKY_TOP[c]) * t) for c in range(3)]
        pygame.draw.line(surf, color, (0, i), (WIDTH, i))
    for i in range(half, HEIGHT):
        t = (i - half) / max(1, HEIGHT - half)
        color = [int(GROUND_NEAR[c] + (GROUND_FAR[c] - GROUND_NEAR[c]) * (1 - t)) for c in range(3)]
        pygame.draw.line(surf, color, (0, i), (WIDTH, i))
    return surf


class Renderer:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("FPV Drone Racing Sim")
        self.font = pygame.font.SysFont("consolas", 16)
        self.big_font = pygame.font.SysFont("consolas", 36, bold=True)
        self.focal = FOCAL_PX
        self.background = _build_background()

    def project(self, point, cam_pos, cam_yaw):
        rel_x = point[0] - cam_pos[0]
        rel_y = point[1] - cam_pos[1]
        rel_z = point[2] - cam_pos[2]

        cos_y = math.cos(-cam_yaw)
        sin_y = math.sin(-cam_yaw)
        cx = rel_x * cos_y - rel_z * sin_y
        cz = rel_x * sin_y + rel_z * cos_y
        cy = rel_y

        if cz < NEAR_CLIP:
            return None

        sx = WIDTH / 2.0 + (cx / cz) * self.focal
        sy = HEIGHT / 2.0 - (cy / cz) * self.focal
        return (sx, sy, cz)

    def draw_ground_grid(self, cam_pos, cam_yaw):
        for z in range(0, 120, 10):
            pts = []
            for x in (-20, 20):
                p = self.project((x, 0.0, z), cam_pos, cam_yaw)
                if p:
                    pts.append((p[0], p[1]))
            if len(pts) == 2:
                pygame.draw.line(self.screen, (40, 90, 40), pts[0], pts[1], 1)
        for x in range(-20, 21, 5):
            pts = []
            for z in (0, 120):
                p = self.project((x, 0.0, z), cam_pos, cam_yaw)
                if p:
                    pts.append((p[0], p[1]))
            if len(pts) == 2:
                pygame.draw.line(self.screen, (40, 90, 40), pts[0], pts[1], 1)

    def build_gate_bars(self, gate, cam_pos, cam_yaw):
        hw, hh, bar = gate.half_w, gate.half_h, gate.half_w * GATE_BAR_RATIO
        z = gate.z
        outer = [
            (gate.x - hw, gate.y - hh, z),
            (gate.x + hw, gate.y - hh, z),
            (gate.x + hw, gate.y + hh, z),
            (gate.x - hw, gate.y + hh, z),
        ]
        inner = [
            (gate.x - hw + bar, gate.y - hh + bar, z),
            (gate.x + hw - bar, gate.y - hh + bar, z),
            (gate.x + hw - bar, gate.y + hh - bar, z),
            (gate.x - hw + bar, gate.y + hh - bar, z),
        ]

        proj_outer = [self.project(p, cam_pos, cam_yaw) for p in outer]
        proj_inner = [self.project(p, cam_pos, cam_yaw) for p in inner]
        if any(p is None for p in proj_outer) or any(p is None for p in proj_inner):
            return None

        avg_depth = sum(p[2] for p in proj_outer) / 4.0
        bars = []
        for i in range(4):
            j = (i + 1) % 4
            quad = [proj_outer[i][:2], proj_outer[j][:2], proj_inner[j][:2], proj_inner[i][:2]]
            bars.append(quad)
        return avg_depth, bars

    def render(self, state):
        with state.lock:
            cam_pos = tuple(state.pos)
            cam_yaw = state.yaw
            gates = list(state.gates)
            crashed = state.crashed
            crash_count = state.crash_count
            gates_passed = state.gates_passed
            pos_copy = tuple(state.pos)
            speed = math.sqrt(sum(v * v for v in state.vel))

        self.screen.blit(self.background, (0, 0))
        self.draw_ground_grid(cam_pos, cam_yaw)

        drawables = []
        for gate in gates:
            result = self.build_gate_bars(gate, cam_pos, cam_yaw)
            if result:
                drawables.append(result)
        drawables.sort(key=lambda d: -d[0])
        for _, bars in drawables:
            for quad in bars:
                pygame.draw.polygon(self.screen, GATE_COLOR, quad)
                pygame.draw.polygon(self.screen, GATE_EDGE_COLOR, quad, 1)

        self.draw_hud(pos_copy, cam_yaw, speed, crash_count, gates_passed)

        if crashed:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((255, 0, 0, 70))
            self.screen.blit(overlay, (0, 0))
            text = self.big_font.render("CRASHED", True, CRASH_COLOR)
            self.screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT // 2 - 20))

        pygame.draw.rect(self.screen, (60, 60, 60), RESET_BUTTON_RECT, border_radius=6)
        pygame.draw.rect(self.screen, (200, 200, 200), RESET_BUTTON_RECT, 2, border_radius=6)
        label = self.font.render("RESET", True, (255, 255, 255))
        self.screen.blit(
            label,
            (RESET_BUTTON_RECT.centerx - label.get_width() // 2,
             RESET_BUTTON_RECT.centery - label.get_height() // 2),
        )

        pygame.display.flip()

    def draw_hud(self, pos, yaw, speed, crash_count, gates_passed):
        lines = [
            f"X: {pos[0]:6.2f}  Y: {pos[1]:6.2f}  Z: {pos[2]:6.2f}",
            f"YAW: {math.degrees(yaw):6.1f} deg   SPD: {speed:5.2f} m/s",
            f"GATES: {gates_passed}   CRASHES: {crash_count}",
        ]
        for i, line in enumerate(lines):
            surf = self.font.render(line, True, HUD_COLOR)
            self.screen.blit(surf, (10, 10 + i * 20))

    def frame_to_bytes(self):
        buf = io.BytesIO()
        pygame.image.save(self.screen, buf, "frame.jpg")
        return buf.getvalue()
