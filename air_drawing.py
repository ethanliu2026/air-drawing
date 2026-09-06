from cvzone.HandTrackingModule import HandDetector
import cv2
from gpiozero import Servo, LED, Button as GPIOButton
from gpiozero.pins.pigpio import PiGPIOFactory
import pygame
import numpy as np
import time

# Initialize Pygame
pygame.init()

# Screen dimensions
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720

# Initialize Pygame display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Air Drawing with Servo")

# Initialize GPIO components
# Use pigpio for better PWM (optional, falls back to default if not available)
try:
    factory = PiGPIOFactory()
    servo = Servo(12, pin_factory=factory)
except:
    servo = Servo(12)

# Individual LEDs for each color
led_red = LED(5)      # Red LED on GPIO 5
led_blue = LED(17)    # Blue LED on GPIO 17
led_yellow = LED(6)   # Yellow LED on GPIO 6
led_green = LED(22)   # Green LED on GPIO 22
led_white = LED(27)   # White LED on GPIO 27 (for black brush)

all_leds = [led_red, led_green, led_blue, led_yellow, led_white]

# Physical buttons/switch
color_button = GPIOButton(13, pull_up=True, bounce_time=0.1)   # Button for color cycling (GPIO 13)
tool_switch = GPIOButton(19, pull_up=True, bounce_time=0.1)    # Switch for brush/eraser (GPIO 19)

# Initialize webcam
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Initialize HandDetector
detector = HandDetector(staticMode=False, maxHands=1, modelComplexity=1, detectionCon=0.7, minTrackCon=0.5)

# Colors for drawing (5 colors only: Red, Green, Blue, Yellow, Black)
colors_bgr = [
    (0, 0, 255),      # Red
    (0, 255, 0),      # Green
    (255, 0, 0),      # Blue
    (0, 255, 255),    # Yellow
    (0, 0, 0)         # Black
]

colors_rgb = [
    (255, 0, 0),      # Red
    (0, 255, 0),      # Green
    (0, 0, 255),      # Blue
    (255, 255, 0),    # Yellow
    (0, 0, 0)         # Black
]

color_names = ["Red", "Green", "Blue", "Yellow", "Black"]

# Servo angles for each color (0° to 180°)
color_angles = [0, 45, 90, 135, 180]

# Drawing state
current_color_index = 0
current_tool = "brush"  # "brush" or "eraser"
brush_size = 5

# Button class for virtual buttons
class Button:
    def __init__(self, x, y, width, height, color, text, icon=None):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color
        self.text = text
        self.icon = icon
        self.hovered = False
        self.hover_time = 0
        
    def draw(self, surface):
        # Draw button background
        color = self.color
        if self.hovered:
            # Lighten color when hovered
            color = tuple(min(c + 50, 255) for c in self.color)
        
        pygame.draw.rect(surface, color, (self.x, self.y, self.width, self.height), border_radius=10)
        pygame.draw.rect(surface, (255, 255, 255), (self.x, self.y, self.width, self.height), 3, border_radius=10)
        
        # Draw text
        font = pygame.font.Font(None, 32)
        text_surface = font.render(self.text, True, (255, 255, 255))
        text_rect = text_surface.get_rect(center=(self.x + self.width // 2, self.y + self.height // 2))
        surface.blit(text_surface, text_rect)
        
        # Draw hover progress bar
        if self.hovered and self.hover_time > 0:
            progress = min(self.hover_time / 2.0, 1.0)  # 2 second hover to activate
            bar_width = int(self.width * progress)
            pygame.draw.rect(surface, (0, 255, 0), (self.x, self.y + self.height - 5, bar_width, 5))
    
    def is_over(self, x, y):
        return self.x < x < self.x + self.width and self.y < y < self.y + self.height

# Create virtual clear button
clear_button = Button(50, 30, 120, 60, (150, 150, 150), "Clear")

# Drawing canvas (Pygame surface)
canvas = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
canvas.fill((255, 255, 255))  # White background

# Drawing tracking
prev_x, prev_y = 0, 0
drawing = False

def set_servo_angle(angle):
    """Convert angle (0-180) to servo value (-1 to 1)"""
    servo_value = (angle - 90) / 90
    servo.value = max(-1, min(1, servo_value))

def smooth_servo_transition(current_angle, target_angle, steps=10):
    """Smoothly transition servo from current to target angle"""
    for i in range(steps + 1):
        angle = current_angle + (target_angle - current_angle) * (i / steps)
        set_servo_angle(angle)
        time.sleep(0.02)

def update_leds(color_index, tool):
    """Update LEDs to show current brush color"""
    # Turn off all LEDs first
    for led in all_leds:
        led.off()
    
    if tool == "eraser":
        # Blink white LED for eraser or turn all on
        led_white.on()
    else:
        # Turn on LED corresponding to current color
        if color_index == 0:    # Red
            led_red.on()
        elif color_index == 1:  # Green
            led_green.on()
        elif color_index == 2:  # Blue
            led_blue.on()
        elif color_index == 3:  # Yellow
            led_yellow.on()
        elif color_index == 4:  # Black (show white LED)
            led_white.on()

def on_color_button_press():
    """Handle physical color button press"""
    global current_color_index, current_servo_angle, current_tool
    
    # Cycle to next color
    old_angle = current_servo_angle
    current_color_index = (current_color_index + 1) % len(colors_rgb)
    
    # Update servo if in brush mode
    if current_tool == "brush":
        target_angle = color_angles[current_color_index]
        smooth_servo_transition(old_angle, target_angle)
        current_servo_angle = target_angle
    
    # Update LEDs
    update_leds(current_color_index, current_tool)
    print(f"Color changed to {color_names[current_color_index]}")

def check_tool_switch():
    """Check tool switch state and update tool"""
    global current_tool, current_servo_angle
    
    # Read switch state (LOW = pressed/ON, HIGH = released/OFF)
    # Assuming switch ON = eraser, switch OFF = brush
    if tool_switch.is_pressed:
        new_tool = "eraser"
    else:
        new_tool = "brush"
    
    # Only update if tool changed
    if new_tool != current_tool:
        old_angle = current_servo_angle
        current_tool = new_tool
        
        if current_tool == "eraser":
            target_angle = 180  # Eraser position
        else:
            target_angle = color_angles[current_color_index]
        
        smooth_servo_transition(old_angle, target_angle)
        current_servo_angle = target_angle
        update_leds(current_color_index, current_tool)
        print(f"Tool changed to {current_tool}")

# Set up button callback
color_button.when_pressed = on_color_button_press

# Set initial servo position and LEDs
current_servo_angle = color_angles[current_color_index]
set_servo_angle(current_servo_angle)
update_leds(current_color_index, current_tool)

# Main loop
running = True
clock = pygame.time.Clock()

# Button hover tracking
button_hover_start = {}

try:
    print("Air Drawing Started!")
    print("=" * 50)
    print("Hardware Controls:")
    print("- Physical BUTTON (GPIO 13) = Cycle colors")
    print("- Physical SWITCH (GPIO 19) = Toggle Brush/Eraser")
    print()
    print("LEDs:")
    print("- Red LED (GPIO 5) = Red brush")
    print("- Green LED (GPIO 22) = Green brush")
    print("- Blue LED (GPIO 17) = Blue brush")
    print("- Yellow LED (GPIO 6) = Yellow brush")
    print("- White LED (GPIO 27) = Black brush OR Eraser")
    print()
    print("Hand Gestures:")
    print("- Index finger up only = Draw")
    print("- Fist (all fingers down) = Click virtual Clear button")
    print("- Press 'q' to quit")
    print("=" * 50)
    
    while running:
        # Check tool switch state every loop
        check_tool_switch()
        
        # Handle Pygame events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False
        
        # Capture frame from webcam
        success, img = cap.read()
        if not success:
            print("Failed to read from camera")
            break
        
        # Flip image for mirror effect
        img = cv2.flip(img, 1)
        
        # Find hands
        hands, img = detector.findHands(img, draw=True, flipType=False)
        
        # Clear Pygame screen
        screen.fill((240, 240, 240))
        
        # Draw canvas on screen
        screen.blit(canvas, (0, 0))
        
        # Draw clear button
        clear_button.draw(screen)
        
        # Draw color indicator (larger)
        current_color_rgb = colors_rgb[current_color_index]
        pygame.draw.circle(screen, current_color_rgb, (250, 60), 30)
        pygame.draw.circle(screen, (255, 255, 255), (250, 60), 30, 3)
        
        # Draw tool indicator
        tool_color = (0, 0, 0) if current_tool == "brush" else (255, 255, 255)
        pygame.draw.circle(screen, tool_color, (350, 60), 30)
        pygame.draw.circle(screen, (0, 0, 0), (350, 60), 30, 3)
        
        # Draw status text
        font = pygame.font.Font(None, 32)
        status_text = f"Tool: {current_tool.upper()} | Color: {color_names[current_color_index]}"
        text_surface = font.render(status_text, True, (0, 0, 0))
        screen.blit(text_surface, (450, 50))
        
        # Draw hardware status
        hw_font = pygame.font.Font(None, 22)
        hw_text = "HW: Color Button (GPIO13) | Tool Switch (GPIO19)"
        hw_surface = hw_font.render(hw_text, True, (100, 100, 100))
        screen.blit(hw_surface, (50, 690))
        
        # Process hand tracking
        if hands:
            hand = hands[0]
            fingers = detector.fingersUp(hand)
            lmList = hand['lmList']
            
            # Get index fingertip position (landmark 8)
            finger_x, finger_y = lmList[8][0], lmList[8][1]
            
            # Scale coordinates to screen size
            screen_x = int(finger_x * SCREEN_WIDTH / 640)
            screen_y = int(finger_y * SCREEN_HEIGHT / 480)
            
            # Check gesture
            finger_count = fingers.count(1)
            is_drawing_gesture = fingers == [0, 1, 0, 0, 0]  # Only index up
            is_click_gesture = fingers == [0, 0, 0, 0, 0]    # Fist
            
            # Draw cursor
            cursor_color = colors_rgb[current_color_index] if current_tool == "brush" else (255, 255, 255)
            pygame.draw.circle(screen, cursor_color, (screen_x, screen_y), brush_size + 2)
            pygame.draw.circle(screen, (0, 0, 0), (screen_x, screen_y), brush_size + 2, 2)
            
            # Check button interactions (only clear button)
            buttons = [clear_button]
            for btn in buttons:
                if btn.is_over(screen_x, screen_y):
                    btn.hovered = True
                    
                    # Track hover time
                    if btn not in button_hover_start:
                        button_hover_start[btn] = time.time()
                    else:
                        btn.hover_time = time.time() - button_hover_start[btn]
                        
                        # Auto-activate after 2 seconds OR on click gesture
                        if btn.hover_time >= 2.0 or is_click_gesture:
                            if btn == clear_button:
                                # Clear canvas
                                canvas.fill((255, 255, 255))
                                print("Canvas cleared")
                            
                            # Reset hover timer
                            button_hover_start[btn] = time.time()
                else:
                    btn.hovered = False
                    btn.hover_time = 0
                    if btn in button_hover_start:
                        del button_hover_start[btn]
            
            # Drawing logic
            if is_drawing_gesture and screen_y > 110:  # Below button area
                if drawing and prev_x != 0 and prev_y != 0:
                    # Draw line on canvas
                    draw_color = colors_rgb[current_color_index] if current_tool == "brush" else (255, 255, 255)
                    pygame.draw.line(canvas, draw_color, (prev_x, prev_y), (screen_x, screen_y), brush_size * 2)
                
                prev_x, prev_y = screen_x, screen_y
                drawing = True
            else:
                prev_x, prev_y = 0, 0
                drawing = False
        else:
            prev_x, prev_y = 0, 0
            drawing = False
            # Reset all button hovers
            for btn in [clear_button]:
                btn.hovered = False
                btn.hover_time = 0
            button_hover_start.clear()
        
        # Convert Pygame surface to OpenCV format for display (optional - show in OpenCV window)
        # Update Pygame display
        pygame.display.flip()
        
        # Display camera feed in separate OpenCV window (smaller)
        img_small = cv2.resize(img, (320, 240))
        cv2.imshow("Camera Feed", img_small)
        
        # Check for quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            running = False
        
        clock.tick(30)  # 30 FPS

except KeyboardInterrupt:
    print("\nProgram interrupted by user")

finally:
    # Cleanup
    print("Performing cleanup...")
    for led in all_leds:
        led.off()
    servo.value = 0
    servo.close()
    color_button.close()
    tool_switch.close()
    cap.release()
    cv2.destroyAllWindows()
    pygame.quit()
    print("Cleanup complete")