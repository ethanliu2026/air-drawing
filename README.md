# ✍️ Air Drawing — Gesture-Controlled Drawing with Physical Feedback

**Draw in the air with your finger. A servo and LEDs physically show what you're doing.**

A touchless drawing application: you draw on screen by moving your index finger in front of a webcam, using hand gestures to draw, switch colors, and clear the canvas. What makes it different from a normal drawing app is the **physical feedback** — a servo motor rotates to point at your currently selected color, and per-color LEDs light up, bridging the on-screen action with real hardware.

Built on a Raspberry Pi 5 with computer-vision hand tracking (CVZone / MediaPipe) and GPIO hardware control (gpiozero).

<!-- 👇 REPLACE with a demo GIF/video — a clip of drawing in the air while the servo swings to match the color is the perfect visual. -->
<!-- ![demo](media/demo.gif) -->

---

## How it works

- **Draw:** hold up just your index finger — the fingertip becomes a pen and draws on the canvas
- **Click:** make a fist over an on-screen button to activate it (or hover for 2 seconds)
- **Change color:** press a physical button — cycles through colors, and the servo rotates to point at the selected one
- **Brush / eraser:** flip a physical switch — the servo swings to the eraser position
- **Clear:** fist over the on-screen Clear button
- **Physical feedback:** an LED lights up for the active color; the servo acts as a real-world pointer/indicator

Gestures are read from MediaPipe's 21 hand landmarks: `fingersUp()` returns which fingers are extended, so `[0,1,0,0,0]` (index only) means *draw* and `[0,0,0,0,0]` (fist) means *click*. The index fingertip (landmark 8) is mapped from camera space to screen space to position the pen.

## Tech stack

**Software:** Python · CVZone · MediaPipe (hand tracking) · OpenCV · Pygame (canvas & UI) · gpiozero
**Hardware:** Raspberry Pi 5 · USB webcam · SG90 servo (color pointer) · 5× LEDs · physical button + switch · breadboard

## Interaction design

The project is really about **multi-modal interaction** — combining three input/output channels into one coherent experience:

| Channel | Role |
|---|---|
| Hand gestures (vision) | Drawing, clicking |
| Physical button / switch | Color cycling, brush/eraser toggle |
| Servo + LEDs | Real-world feedback on current state |

Managing this cleanly meant a small **state machine** (current color, current tool, drawing/idle) with each input updating shared state and each output (canvas, servo, LEDs) reflecting it — plus smooth servo interpolation so the pointer glides between positions instead of snapping.

## Hardware & wiring

<details>
<summary>GPIO pin assignments (final version)</summary>

| Component | GPIO | Notes |
|---|---|---|
| Servo (color pointer) | 12 | PWM; `pigpio` pin factory for smoother signal |
| Red LED | 5 | Per-color indicator |
| Blue LED | 17 | |
| Yellow LED | 6 | |
| Green LED | 22 | |
| White LED | 27 | Black brush / eraser indicator |
| Color button | 13 | Cycles colors |
| Tool switch | 19 | Brush ↔ eraser |

Servo angle is mapped from a color index (0–4 → 0°–180°) and converted to gpiozero's −1…1 range. Use an **external 5V supply** for the servo and a **common ground** with the Pi; LEDs use 220 Ω resistors.

</details>

## Design evolution

Three iterations, in `archive/`:

- **v1** (`air_drawing_v1_servo_only.py`) — servo pointer + on-screen virtual buttons only
- **v3** (`air_drawing_v3_rgbled.py`) — added a single RGB LED + physical button/switch
- **Final** (`air_drawing.py`) — individual per-color LEDs, physical button + switch, refined cleanup

## Running it

> Built for a Raspberry Pi 5 with the servo, LEDs, button, and switch wired as above. Needs a camera and a display.

```bash
pip install cvzone opencv-python mediapipe gpiozero pygame numpy
python air_drawing.py
```

Gestures: **index finger up** = draw · **fist** = click · **physical button** = cycle color · **switch** = brush/eraser · **Q** = quit.

---

*A physical-computing project exploring touchless, multi-modal interaction — computer-vision gesture control combined with real-world servo and LED feedback.*
