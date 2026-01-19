import sys
import os
import time
import requests
import logging
from PIL import Image, ImageDraw, ImageFont

# --- CONFIGURATION ---
# Pointing to the waveshare_epd folder inside your /app directory
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from waveshare_epd import epd5in83_V2 

logging.basicConfig(level=logging.INFO)

# --- DATA FETCHING ---

def get_weather_data(city="Rochester,NY"):
    """Fetches current conditions and a 3-day forecast from wttr.in"""
    try:
        # Current: Condition + Temp (Fahrenheit) + Precip %
        # Change 'u' to 'm' if you prefer Metric/Celsius
        curr_url = f"https://wttr.in/{city}?u&format=%C+%t+%p"
        current = requests.get(curr_url, timeout=10).text.strip()
        
        # Forecast: Day + High/Low
        fore_url = f"https://wttr.in/{city}?u&format=%l:+%h/%L\n"
        forecast = requests.get(fore_url, timeout=10).text.strip().split('\n')[:3]
        
        return current, forecast
    except Exception as e:
        logging.error(f"Weather error: {e}")
        return "Weather Offline", ["N/A", "N/A", "N/A"]

def get_cpu_temp():
    """Reads Pi CPU temperature directly from system files"""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = int(f.read()) / 1000
        return f"{temp:.1f}°C"
    except:
        return "N/A"

# --- DISPLAY LOGIC ---

def update_display():
    try:
        logging.info("Waking up e-Paper...")
        epd = epd5in83_V2.EPD()
        epd.init()

        # Create blank canvas (648x480 for 5.83" V2)
        canvas = Image.new('1', (epd.width, epd.height), 255)
        draw = ImageDraw.Draw(canvas)

        # Fonts (Assumes fonts-dejavu-core is installed via Dockerfile)
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        font_lg = ImageFont.truetype(font_path, 80)
        font_md = ImageFont.truetype(font_path, 40)
        font_sm = ImageFont.truetype(font_path, 26)

        # --- DRAWING: HEADER & TIME ---
        # Draw a black header bar
        draw.rectangle((0, 0, epd.width, 100), fill=0)
        draw.text((20, 10), time.strftime('%H:%M'), font=font_lg, fill=255)
        draw.text((320, 20), "ROCHESTER, NY", font=font_sm, fill=255)
        draw.text((320, 55), time.strftime('%A, %b %d'), font=font_sm, fill=255)

        # --- DRAWING: CURRENT WEATHER ---
        curr_weather, weekly = get_weather_data("Rochester,NY")
        draw.text((20, 120), "CURRENT CONDITIONS", font=font_sm, fill=0)
        draw.text((20, 155), curr_weather, font=font_md, fill=0)

        # Horizontal Divider
        draw.line((20, 225, epd.width-20, 225), fill=0, width=2)

        # --- DRAWING: 3-DAY FORECAST (Lower Left) ---
        draw.text((20, 240), "3-DAY FORECAST", font=font_sm, fill=0)
        y_pos = 285
        for day in weekly:
            draw.text((20, y_pos), day, font=font_md, fill=0)
            y_pos += 55

        # --- DRAWING: SYSTEM INFO (Lower Right) ---
        # Vertical Divider
        draw.line((400, 240, 400, 450), fill=0, width=2)
        
        draw.text((420, 240), "SYSTEM STATUS", font=font_sm, fill=0)
        draw.text((420, 290), f"CPU: {get_cpu_temp()}", font=font_sm, fill=0)
        draw.text((420, 330), f"UP: {time.strftime('%H:%M')}", font=font_sm, fill=0)
        draw.text((420, 370), "Interval: 5m", font=font_sm, fill=0)

        # --- PUSH TO HARDWARE ---
        logging.info("Pushing to display...")
        epd.display(epd.getbuffer(canvas))
        
        logging.info("Putting display to deep sleep...")
        epd.sleep()

    except Exception as e:
        logging.error(f"Display update failed: {e}")

# --- MAIN LOOP ---

if __name__ == "__main__":
    logging.info("E-Paper Dashboard Started.")
    while True:
        update_display()
        logging.info("Cycle complete. Sleeping for 5 minutes...")
        time.sleep(300)