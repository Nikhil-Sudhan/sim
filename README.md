# FPV Drone Racing Sim

Python + Pygame FPV drone racing sim with a REST API for external (e.g. vision-model) control.

## Run

```
pip install -r requirements.txt
python main.py
```

A Pygame window opens (640x480 FPV view) and a Flask API starts on `http://127.0.0.1:5000` in a background thread.

## API

- `POST /control` `{ "x": float, "y": float, "z": float, "yaw": float }` — sets the target the drone eases toward (radians for yaw).
- `POST /reset` — resets the drone to the start position and randomizes gate placement.
- `GET /frame` — returns the current FPV view as a JPEG (640x480).
- `GET /status` — full telemetry:
  ```json
  {
    "position":     {"x":0,"y":0,"z":0},
    "velocity":     {"x":0,"y":0,"z":0},
    "acceleration": {"x":0,"y":0,"z":0},
    "speed": 0.0, "yaw": 0.0, "yaw_rate": 0.0,
    "crashed": false, "alive": true, "crash_count": 0,
    "gates_passed": 0, "gates_total": 5,
    "next_gate": {"x":0,"y":0,"z":15,"half_w":2.5,"half_h":2.0,"distance":15.0},
    "time_alive": 0.0
  }
  ```
- `GET /gates` — ground-truth gate geometry **and camera intrinsics**, so a vision
  client can turn an apparent gate width into a real distance and check its own
  obstacle-center estimate:
  ```json
  {
    "camera": {"width":640,"height":480,"fov_deg":90.0,"focal_px":320.0},
    "gates": [{"x":0,"y":2.5,"z":15,"half_w":2.5,"half_h":2.0,
               "width":5.0,"height":4.0,"thickness":1.0}]
  }
  ```

In-window controls: click the on-screen **RESET** button, or press `R`.

## Performance notes (why it no longer stutters)

- The sky/ground gradient is rendered **once** into a cached surface and blitted each
  frame, instead of redrawing 480 gradient scanlines every frame.
- The FPV JPEG is encoded at most **30 Hz**, and only while a client is actively
  polling `/frame` — so an idle window spends no time encoding.

## Build a standalone .exe

```
pip install --user -U setuptools "jaraco.functools" "jaraco.context" "jaraco.text"
pyinstaller --onefile --name FPVDroneSim --collect-submodules jaraco --hidden-import pkg_resources main.py
```

The `jaraco`/`pkg_resources` flags are required — without them the exe crashes on launch with
`ModuleNotFoundError: No module named 'jaraco'` because PyInstaller's pkg_resources runtime hook
doesn't auto-bundle setuptools' vendored `jaraco` packages.

The resulting `dist/FPVDroneSim.exe` opens the Pygame window and starts the API on `localhost:5000`, same as running `python main.py`.

## Notes

- World axes: `x` = left/right, `y` = altitude (ground at `y=0`), `z` = forward depth. Gates are spaced along `z`; fly through their opening or it's a crash.
- Physics is a spring-damper: the drone accelerates toward the commanded target position/yaw with drag and a constant gravity pull on `y`, so motion has lag/inertia rather than teleporting. Velocity is clamped to a terminal speed (`MAX_SPEED` in `physics.py`), and per-axis acceleration is exposed in telemetry.
- To **hold** an altitude the commanded `target_y` must sit `GRAVITY/ATTRACT_K` (≈1.33 m) above current `y` — that bias cancels gravity. The vision client accounts for this.
- Flying forward through a gate's opening increments `gates_passed`; clipping the gate plane outside the opening is a crash.
- Crash triggers a brief freeze (1.5s) then auto-reset; gates re-randomize on every reset (manual or automatic).
