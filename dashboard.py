"""GranJam live IMU + ToF dashboard for the Raspberry Pi 5.

Reads the existing Arduino CSV stream on /dev/ttyACM0, logs every valid
CSV row, and plots a rolling 30-second view using Dash.
"""
import csv
import math
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path

import serial
from dash import Dash, Input, Output, dcc, html
import plotly.graph_objects as go

PORT = "/dev/ttyACM0"
BAUD = 115200
WINDOW_SECONDS = 30
FIELDS = [
    "ms", "accel_roll_deg", "kalman_roll_deg",
    "accel_pitch_deg", "kalman_pitch_deg", "tof_raw_mm",
    "tof_filtered_mm", "tof_valid",
]

samples = deque(maxlen=1200)
lock = threading.Lock()
connection_error = None


def read_arduino():
    global connection_error
    data_dir = Path(__file__).resolve().parent / "data"
    data_dir.mkdir(exist_ok=True)
    filename = data_dir / f"dashboard_{datetime.now():%Y%m%d_%H%M%S}.csv"

    try:
        with serial.Serial(PORT, BAUD, timeout=1) as device, \
                filename.open("w", newline="") as output:
            writer = csv.writer(output)
            writer.writerow(FIELDS)
            output.flush()
            print(f"Connected to {PORT}; saving data to {filename}")
            time.sleep(2)  # Uno resets on opening the serial port

            while True:
                line = device.readline().decode("utf-8", errors="replace").strip()
                if not line or line.startswith("#") or line.startswith("ms,"):
                    continue
                fields = next(csv.reader([line]))
                if len(fields) != len(FIELDS):
                    continue
                try:
                    values = [float(v) for v in fields]
                    if not all(math.isfinite(v) for v in values):
                        continue
                    if int(values[7]) not in (0, 1):
                        continue
                    valid = int(values[7]) == 1
                    sample = {
                        "time": time.monotonic(),
                        "roll": values[2],
                        "pitch": values[4],
                        "raw": values[5] if valid else None,
                        "filtered": values[6] if valid else None,
                        "valid": valid,
                    }
                except (ValueError, IndexError):
                    continue

                with lock:
                    samples.append(sample)
                writer.writerow(fields)
                output.flush()

    except (serial.SerialException, OSError) as exc:
        connection_error = str(exc)
        print(f"Arduino connection stopped: {exc}")


def make_graph(data, channels, y_title):
    fig = go.Figure()
    if data:
        last = data[-1]["time"]
        visible = [s for s in data if last - s["time"] <= WINDOW_SECONDS]
        x = [s["time"] - last for s in visible]
        for key, label in channels:
            fig.add_trace(go.Scatter(
                x=x, y=[s[key] for s in visible],
                name=label, mode="lines", connectgaps=False,
            ))
    fig.update_layout(
        template="plotly_white", height=350, margin=dict(l=50, r=20, t=15, b=45),
        xaxis_title="Seconds before latest sample",
        yaxis_title=y_title, legend=dict(orientation="h", y=1.16),
        uirevision="keep",
    )
    fig.update_xaxes(range=[-WINDOW_SECONDS, 0])
    return fig


app = Dash(__name__)
CARD = {"background": "#f1f5f9", "padding": "18px", "borderRadius": "12px"}


def card(title, name):
    return html.Div([
        html.Div(title, style={"fontSize": "14px", "color": "#475569"}),
        html.H2(id=name, children="--", style={"margin": "8px 0 0"}),
    ], style=CARD)


app.layout = html.Div([
    html.H1("GranJam | Live Sensor Dashboard"),
    html.P(id="connection-status", children="Connecting to Arduino..."),
    html.Div([
        card("Kalman Roll", "roll-value"),
        card("Kalman Pitch", "pitch-value"),
        card("ToF Raw", "raw-value"),
        card("ToF Filtered", "filtered-value"),
    ], style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(170px, 1fr))", "gap": "12px"}),
    html.Div([
        dcc.Graph(id="imu-graph"),
        dcc.Graph(id="tof-graph"),
    ], style={"display": "grid", "gridTemplateColumns": "repeat(auto-fit, minmax(320px, 1fr))", "gap": "12px"}),
    html.P("CSV recording starts automatically. To stop, press Ctrl+C in the VS Code terminal."),
    dcc.Interval(id="refresh", interval=500, n_intervals=0),
], style={"maxWidth": "1300px", "margin": "auto", "padding": "20px", "fontFamily": "Arial, sans-serif"})


@app.callback(
    Output("connection-status", "children"),
    Output("roll-value", "children"),
    Output("pitch-value", "children"),
    Output("raw-value", "children"),
    Output("filtered-value", "children"),
    Output("imu-graph", "figure"),
    Output("tof-graph", "figure"),
    Input("refresh", "n_intervals"),
)
def update_dashboard(_):
    with lock:
        data = list(samples)
    imu = make_graph(data, [("roll", "Kalman Roll"), ("pitch", "Kalman Pitch")], "Angle (degrees)")
    tof = make_graph(data, [("raw", "Raw"), ("filtered", "Filtered")], "Distance (mm)")
    if connection_error:
        return (f"Connection error: {connection_error}", "--", "--", "--", "--", imu, tof)
    if not data:
        return ("Waiting for Arduino CSV measurements...", "--", "--", "--", "--", imu, tof)
    s = data[-1]
    age = time.monotonic() - s["time"]
    status = "Live • recording to CSV" if age <= 2 else f"No new data for {age:.1f} seconds"
    raw = f"{s['raw']:.0f} mm" if s["valid"] else "Invalid"
    filtered = f"{s['filtered']:.1f} mm" if s["valid"] else "Invalid"
    return status, f"{s['roll']:.2f}°", f"{s['pitch']:.2f}°", raw, filtered, imu, tof


if __name__ == "__main__":
    threading.Thread(target=read_arduino, daemon=True).start()
    app.run(host="127.0.0.1", port=8050, debug=False)
