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
- `GET /status` — `{ position: {x,y,z}, yaw, crashed, alive, crash_count }`.

In-window controls: click the on-screen **RESET** button, or press `R`.

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
- Physics is a simple spring-damper: the drone accelerates toward the commanded target position/yaw with drag and a constant gravity pull on `y`, so motion has lag/inertia rather than teleporting.
- Crash triggers a brief freeze (1.5s) then auto-reset; gates re-randomize on every reset (manual or automatic).
