import threading
import time

import pygame

from state import SimState
from gates import generate_random_gates
from physics import update as physics_update
from renderer import Renderer, RESET_BUTTON_RECT
from api import create_app

# Cap JPEG encoding at 30 Hz. Encoding a 640x480 JPEG on every 60 Hz frame
# (whether or not anyone is watching) was a big chunk of the old stutter.
ENCODE_INTERVAL = 1.0 / 30.0


def run_api(state, get_frame_bytes):
    app = create_app(state, get_frame_bytes)
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False, threaded=True)


def main():
    gates = generate_random_gates()
    state = SimState(gates)
    renderer = Renderer()

    api_thread = threading.Thread(target=run_api, args=(state, state.get_frame_bytes), daemon=True)
    api_thread.start()

    clock = pygame.time.Clock()
    running = True
    last_encode = 0.0
    # Encode the very first frame so an early /frame poll isn't empty.
    state.set_frame_bytes(renderer.frame_to_bytes())

    while running:
        dt = min(clock.tick(60) / 1000.0, 0.05)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if RESET_BUTTON_RECT.collidepoint(event.pos):
                    state.reset(new_gates=generate_random_gates())
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    state.reset(new_gates=generate_random_gates())

        physics_update(state, dt)
        renderer.render(state)

        now = time.monotonic()
        if (now - last_encode) >= ENCODE_INTERVAL and state.client_wants_frame(now):
            state.set_frame_bytes(renderer.frame_to_bytes())
            last_encode = now

    pygame.quit()


if __name__ == "__main__":
    main()
