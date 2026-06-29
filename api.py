from flask import Flask, request, jsonify, Response

from gates import generate_random_gates
from renderer import WIDTH, HEIGHT, FOV_DEG, FOCAL_PX


def create_app(state, get_frame_bytes):
    app = Flask(__name__)

    @app.post("/control")
    def control():
        data = request.get_json(force=True, silent=True) or {}
        try:
            x = float(data["x"])
            y = float(data["y"])
            z = float(data["z"])
            yaw = float(data["yaw"])
        except (KeyError, TypeError, ValueError):
            return jsonify({"error": "expected numeric x, y, z, yaw"}), 400
        state.set_target(x, y, z, yaw)
        return jsonify({"ok": True})

    @app.post("/reset")
    def reset():
        state.reset(new_gates=generate_random_gates())
        return jsonify({"ok": True})

    @app.get("/frame")
    def frame():
        state.note_frame_request()
        data = get_frame_bytes()
        return Response(data, mimetype="image/jpeg")

    @app.get("/status")
    def status():
        return jsonify(state.snapshot_status())

    @app.get("/gates")
    def gates():
        # Ground-truth gate geometry + camera intrinsics. The vision client
        # uses the intrinsics for analytic distance and the geometry to score
        # how accurate its SAM/YOLO obstacle-center estimate is.
        return jsonify({
            "camera": {
                "width": WIDTH,
                "height": HEIGHT,
                "fov_deg": FOV_DEG,
                "focal_px": FOCAL_PX,
            },
            "gates": state.snapshot_gates(),
        })

    return app
