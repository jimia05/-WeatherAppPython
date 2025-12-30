import customtkinter as ctk
from tkinter import messagebox
from PIL import Image, ImageTk
import requests
import csv

api_key = 'a393391d1b3e743ef773678071e25d93'

# --- Load city/country data from CSV (now using full country name) ---
city_country_list = []
with open('/Users/jimiaderele/Desktop/worldcities.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        city_country_list.append({
            "city": row["city_ascii"],
            "country": row["country"],  # Use full country name
            "iso2": row["iso2"]
        })

def on_city_entry_change(event):
    typed = city_entry.get().strip().lower()
    if not typed:
        hide_suggestions()
        return
    matches = [
        f"{c['city']}, {c['country']}"
        for c in city_country_list
        if typed in c['city'].lower()
    ][:8]  # Limit to 8 suggestions
    show_suggestions(matches, target="city")

def on_country_entry_change(event):
    typed = country_entry.get().strip().lower()
    if not typed:
        hide_suggestions()
        return
    # Find all cities in countries matching the typed country name (case-insensitive, partial match)
    matches = [
        f"{c['city']}, {c['country']}"
        for c in city_country_list
        if typed in c['country'].lower()
    ][:8]  # Limit to 8 suggestions
    show_suggestions(matches, target="country")

def show_suggestions(matches, target):
    hide_suggestions()
    if not matches:
        return
    # Position the suggestion window below the appropriate entry
    entry_widget = city_entry if target == "city" else country_entry
    x = window.winfo_x() + entry_widget.winfo_rootx() - window.winfo_rootx()
    y = window.winfo_y() + entry_widget.winfo_rooty() - window.winfo_rooty() + 40
    window.suggestion_win = ctk.CTkToplevel(window)
    window.suggestion_win.geometry(f"300x{min(200, 30*len(matches))}+{x}+{y}")
    window.suggestion_win.overrideredirect(True)
    for match in matches:
        btn = ctk.CTkButton(window.suggestion_win, text=match, width=280, font=MONO_FONT,
                            command=lambda m=match: select_city(m))
        btn.pack(anchor="w", padx=5, pady=0)

def hide_suggestions():
    if hasattr(window, "suggestion_win") and window.suggestion_win:
        window.suggestion_win.destroy()
        window.suggestion_win = None

def select_city(match):
    city, country = [x.strip() for x in match.split(",")]
    city_entry.delete(0, "end")
    city_entry.insert(0, city)
    country_entry.configure(state="normal")
    country_entry.delete(0, "end")
    country_entry.insert(0, country)
    country_entry.configure(state="readonly")
    hide_suggestions()

def get_weather():
    city = city_entry.get().strip()
    country_full = country_entry.get().strip()
    if not city or not country_full:
        messagebox.showerror("Error", "Please enter both a city and a country (e.g. London, United Kingdom).")
        return

    # Find ISO2 code for the selected city/country (required by API)
    iso2 = None
    for c in city_country_list:
        if c["city"].lower() == city.lower() and c["country"].lower() == country_full.lower():
            iso2 = c["iso2"]
            break
    if not iso2:
        messagebox.showerror("Error", "City and country combination not found.")
        return

    query = f"{city},{iso2}"
    units = units_var.get()
    activity = activity_var.get()
    weather_data = requests.get(
        f"https://api.openweathermap.org/data/2.5/weather?q={query}&units={units}&APPID={api_key}"
    )

    if weather_data.status_code == 200:
        data = weather_data.json()
        weather = data['weather'][0]['main']
        temp = data['main']['temp']
        feels_like = data['main']['feels_like']
        min_temp = data['main']['temp_min']
        max_temp = data['main']['temp_max']
        wind_speed = data['wind']['speed']

        if units == 'metric':
            temp_unit = '°C'
            wind_unit = 'km/h'
            wind_speed_display = round(wind_speed * 3.6)
        elif units == 'imperial':
            temp_unit = '°F'
            wind_unit = 'mph'
            wind_speed_display = round(wind_speed)

        temp_celsius = temp if units == 'metric' else (temp - 32) * 5 / 9
        wind_kmh = wind_speed * 3.6 if units == 'metric' else wind_speed * 1.60934

        weather_labels["condition"].configure(
            text=f"🌤️  {weather} ({data['name']}, {country_full})"
        )
        weather_labels["temp"].configure(
            text=f"🌡️  Temperature: {round(temp)}{temp_unit} (feels like {round(feels_like)}{temp_unit})"
        )
        weather_labels["min"].configure(text=f"🔻 Min: {round(min_temp)}{temp_unit}")
        weather_labels["max"].configure(text=f"🔺 Max: {round(max_temp)}{temp_unit}")
        weather_labels["wind"].configure(text=f"💨 Wind: {wind_speed_display} {wind_unit}")

        advice = verdict(temp_celsius, wind_kmh, activity)
        if advice:
            advice_label.configure(text=f"\n{advice.strip()}")
        else:
            advice_label.configure(text="")
    else:
        error_data = weather_data.json()
        messagebox.showerror("Error", f"Error: {error_data.get('message', 'Unknown error')}")

def verdict(temp, wind_speed, activity):
    thresholds = {
        "Beach": {
            "temp_min": 15,
            "temp_max": 30,
            "wind_max": 20,
            "cold_msg": "Conditions are too cool for beach activities.",
            "hot_msg": "There is a high risk of sun exposure; take appropriate precautions.",
            "wind_msg": "Wind conditions are not suitable for swimming.",
            "good_msg": "Weather conditions are favorable for beach activities."
        },
        "Hiking": {
            "temp_min": 5,
            "temp_max": 25,
            "wind_max": 30,
            "cold_msg": "It is too cold for hiking. Consider postponing your activity.",
            "hot_msg": "It is too hot for hiking. Please exercise caution.",
            "wind_msg": "Wind conditions are not suitable for hiking.",
            "good_msg": "Weather conditions are suitable for hiking."
        },
        "Picnic": {
            "temp_min": 10,
            "temp_max": 28,
            "wind_max": 15,
            "cold_msg": "It is too cold for outdoor dining.",
            "hot_msg": "It is too hot for outdoor dining. Consider rescheduling.",
            "wind_msg": "Wind conditions are not suitable for picnics.",
            "good_msg": "Weather conditions are suitable for a picnic."
        }
    }
    if activity in thresholds:
        t = thresholds[activity]
        advice = ""
        summary = []
        if temp < t["temp_min"]:
            advice += t["cold_msg"] + f" (Current: {round(temp)}°C, Threshold: {t['temp_min']}°C)\n"
            summary.append(f"Temperature is below the recommended minimum.")
        elif temp > t["temp_max"]:
            advice += t["hot_msg"] + f" (Current: {round(temp)}°C, Threshold: {t['temp_max']}°C)\n"
            summary.append(f"Temperature is above the recommended maximum.")
        if wind_speed > t["wind_max"]:
            advice += t["wind_msg"] + f" (Current: {round(wind_speed)} km/h, Threshold: {t['wind_max']} km/h)\n"
            summary.append(f"Wind speed exceeds the recommended maximum.")
        if not advice:
            advice += t["good_msg"] + f" (Temperature: {round(temp)}°C, Wind: {round(wind_speed)} km/h)\n"
        if summary:
            advice += "\nSummary: " + "; ".join(summary)
        return advice
    return ""

def clear_all():
    city_entry.delete(0, "end")
    country_entry.delete(0, "end")
    for lbl in weather_labels.values():
        lbl.configure(text="")
    advice_label.configure(text="")
    hide_suggestions()

# Set appearance mode and color theme for CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

window = ctk.CTk()
window.geometry("670x670")
window.title("Weather")

# Icon handling remains the same, as PIL and ImageTk are compatible
icon_image = Image.open("weather-icon.jpeg")
icon = ImageTk.PhotoImage(icon_image)
window.iconphoto(True, icon)
window.configure(bg="#000000")

units_var = ctk.StringVar(value="metric")
activity_var = ctk.StringVar(value="Beach")

MONO_FONT = ("Courier New", 16)  # You can adjust the size as needed

label = ctk.CTkLabel(window, text="Enter City and Country Code:", font=MONO_FONT)
label.pack(pady=20)

city_country_frame = ctk.CTkFrame(window, fg_color="transparent")
city_country_frame.pack(pady=10)

city_entry = ctk.CTkEntry(city_country_frame, font=MONO_FONT, width=220, placeholder_text="City")
city_entry.pack(side="left", padx=(0, 10))
city_entry.bind("<KeyRelease>", on_city_entry_change)

country_entry = ctk.CTkEntry(city_country_frame, font=MONO_FONT, width=180, placeholder_text="Country")
country_entry.pack(side="left")
country_entry.bind("<KeyRelease>", on_country_entry_change)

unit_frame = ctk.CTkFrame(window)
unit_frame.pack(pady=10)
ctk.CTkRadioButton(unit_frame, text="Celsius", variable=units_var, value="metric", font=MONO_FONT).pack(side="left")
ctk.CTkRadioButton(unit_frame, text="Fahrenheit", variable=units_var, value="imperial", font=MONO_FONT).pack(side="left")

activity_frame = ctk.CTkFrame(window)
activity_frame.pack(pady=10)
ctk.CTkRadioButton(activity_frame, text="Beach", variable=activity_var, value="Beach", font=MONO_FONT).pack(side="left")
ctk.CTkRadioButton(activity_frame, text="Hiking", variable=activity_var, value="Hiking", font=MONO_FONT).pack(side="left")
ctk.CTkRadioButton(activity_frame, text="Picnic", variable=activity_var, value="Picnic", font=MONO_FONT).pack(side="left")

button = ctk.CTkButton(window, text="GO", command=get_weather, font=MONO_FONT)
button.pack()

clear_button = ctk.CTkButton(window, text="Clear All", command=clear_all, font=MONO_FONT)
clear_button.pack(pady=(5, 15))

weather_frame = ctk.CTkFrame(window, fg_color="#222831", corner_radius=15)
weather_frame.pack(pady=15, padx=20, fill="x")

weather_labels = {
    "condition": ctk.CTkLabel(weather_frame, text="", font=("Courier New", 22, "bold")),
    "temp": ctk.CTkLabel(weather_frame, text="", font=("Courier New", 20)),
    "min": ctk.CTkLabel(weather_frame, text="", font=("Courier New", 18)),
    "max": ctk.CTkLabel(weather_frame, text="", font=("Courier New", 18)),
    "wind": ctk.CTkLabel(weather_frame, text="", font=("Courier New", 18)),
}
for lbl in weather_labels.values():
    lbl.pack(anchor="w", padx=20, pady=2)

advice_frame = ctk.CTkFrame(window, fg_color="#393E46", corner_radius=15)
advice_frame.pack(pady=10, padx=20, fill="x")

advice_label = ctk.CTkLabel(advice_frame, text="", font=("Courier New", 20, "bold"), wraplength=600, justify="left")
advice_label.pack(anchor="w", padx=20, pady=10)

window.suggestion_win = None
window.mainloop()