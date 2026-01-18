import sys
import os
import time
import requests
import subprocess
import logging
from PIL import Image, ImageDraw, ImageFont

# Path to your Waveshare Library
sys.path.insert(0, '/home/crobinson/e-Paper/RaspberryPi_JetsonNano/python/lib')
from waveshare_epd import epd5in83_V2 

logging.basicConfig(level=logging.INFO)

def get_weather(city="Rochester"):
    try:
        # We use format="%C+%t" to get "Sunny +20C"
        url = f"https://wttr.in/{city}?format=%C+%t"
        response = requests.get(url, timeout=10)
        return response.text.strip()
    except:
        return "Weather Offline"

def get_cpu_temp():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = int(f.read()) / 1000
        return f"{temp:.1f}°C"
    except:
        return "N/A"

def update_display():
    try:
        logging.info("Waking up e-Paper...")
        epd = epd5in83_V2.EPD()
        epd.init()

        # Create Canvas (648x480)
        canvas = Image.new('1', (epd.width, epd.height), 255)
        draw = ImageDraw.Draw(canvas)

        # Fonts (Standard paths for Pi)
        font_lg = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 70)
        font_md = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
        font_sm = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)

        # --- DRAWING LAYOUT ---
        # 1. Header Line
        draw.rectangle((0, 0, epd.width, 90), fill=0)
        draw.text((20, 10), "INK-PI STATUS", font=font_lg, fill=255)

        # 2. Time & Date
        draw.text((20, 120), time.strftime('%H:%M'), font=font_lg, fill=0)
        draw.text((20, 200), time.strftime('%A, %B %d'), font=font_sm, fill=0)

        # 3. Weather (Live)
        weather_data = get_weather("London") # Replace with your city
        draw.text((350, 120), "Weather:", font=font_sm, fill=0)
        draw.text((350, 150), weather_data, font=font_md, fill=0)

        # 4. System Stats
        temp = get_cpu_temp()
        draw.text((350, 240), f"CPU Temp: {temp}", font=font_sm, fill=0)

        # 5. Footer Decor
        draw.line((20, 320, epd.width-20, 320), fill=0, width=2)
        draw.text((20, 340), "Auto-refreshing every 15 minutes", font=font_sm, fill=0)

        # --- PUSH TO SCREEN ---
        logging.info("Pushing to display...")
        epd.display(epd.getbuffer(canvas))
        
        logging.info("Putting display to deep sleep...")
        epd.sleep()

    except Exception as e:
        logging.error(f"Display update failed: {e}")

# The Main Infinite Loop
if __name__ == "__main__":
    while True:
        update_display()
        logging.info("Sleeping for 15 minutes...")
        time.sleep(900)
