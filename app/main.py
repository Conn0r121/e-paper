import sys
import os
import time
import requests
import logging
import platform
from PIL import Image, ImageDraw, ImageFont

# --- CONFIGURATION ---
ON_PI = platform.system() == "Linux"
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

if ON_PI:
    from waveshare_epd import epd5in83_V2

logging.basicConfig(level=logging.INFO)

# --- DATA FETCHING ---

def get_weather_data():
    """Automatically detects location via IP and fetches weather"""
    try:
        # 1. Get current city name based on IP
        # This returns a simple string like "Rochester"
        city_res = requests.get("https://ipapi.co/city/", timeout=5)
        city = city_res.text.strip() if city_res.status_code == 200 else ""
        
        # 2. Fetch weather from wttr.in
        # If city is empty, wttr.in still works by using your IP automatically
        curr_url = f"https://wttr.in/{city}?u&format=%C+%t+%p"
        current = requests.get(curr_url, timeout=10).text.strip()
        
        # Forecast: Day + High/Low
        fore_url = f"https://wttr.in/{city}?u&format=%l:+%h/%L\n"
        forecast = requests.get(fore_url, timeout=10).text.strip().split('\n')[:3]
        
        # Return city name so we can update the header too
        return current, forecast, city.upper()
    except Exception as e:
        logging.error(f"Auto-weather error: {e}")
        return "Weather Offline", ["N/A", "N/A", "N/A"], "OFFLINE"

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
        if ON_PI:
            logging.info("Waking up e-Paper...")
            epd = epd5in83_V2.EPD()
            epd.init()
            width, height = epd.width, epd.height
        else:
            logging.info("Running in Windows preview mode")
            width, height = 648, 480  # 5.83" resolution

        canvas = Image.new('1', (width, height), 255)
        draw = ImageDraw.Draw(canvas)

        # Fonts (Assumes fonts-dejavu-core is installed via Dockerfile)
        if ON_PI:
            font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        else:
            font_path = "C:/Windows/Fonts/arialbd.ttf"
        
        font_lg = ImageFont.truetype(font_path, 80)
        font_md = ImageFont.truetype(font_path, 40)
        font_sm = ImageFont.truetype(font_path, 26)

        # --- DRAWING: HEADER & TIME ---
        curr_weather, weekly, detected_city = get_weather_data()
        # Draw a black header bar
        draw.rectangle((0, 0, width - 1, 100), fill=0)
        draw.text((20, 10), time.strftime('%H:%M'), font=font_lg, fill=255)
        draw.text((320, 20), detected_city, font=font_sm, fill=255)
        draw.text((320, 55), time.strftime('%A, %b %d'), font=font_sm, fill=255)

        # --- DRAWING: CURRENT WEATHER ---
        draw.text((20, 120), "CURRENT CONDITIONS", font=font_sm, fill=0)
        draw.text((20, 155), curr_weather, font=font_md, fill=0)

        # Horizontal Divider
        draw.line((20, 225, width-20, 225), fill=0, width=2)

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
        if ON_PI:
            epd.display(epd.getbuffer(canvas))
            epd.sleep()
        else:
            output = "preview.png"
            canvas.save(output)
            logging.info(f"Saved preview to {output}")
            os.startfile(output)


    except Exception as e:
        logging.error(f"Display update failed: {e}")

# --- MAIN LOOP ---

if __name__ == "__main__":
    logging.info("E-Paper Dashboard Started.")
    if ON_PI:
        while True:
            update_display()
            logging.info("Cycle complete. Sleeping for 5 minutes...")
            time.sleep(300)
    else:
        update_display()