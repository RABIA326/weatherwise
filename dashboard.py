import requests
import pandas as pd
import altair as alt
import streamlit as st
from html import escape

st.set_page_config(page_title="Weather Dashboard", page_icon="🌦️", layout="wide")

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

POPULAR_CITIES = ["Islamabad", "Lahore", "Karachi", "London", "New York", "Dubai", "Tokyo", "Paris"]

# theme name: (gradient start, gradient end, text colour, chart colour, is_dark)
THEMES = {
    "clear":   ("#FF9A3C", "#FFD86B", "#3A2100", "#D9480F", False),
    "partly":  ("#4C9AF5", "#BFE3FA", "#0B2545", "#1D4ED8", False),
    "cloudy":  ("#6B7C8C", "#C3CED8", "#14202B", "#1E3A5F", False),
    "fog":     ("#8E9EAB", "#E3E8EC", "#1F2A33", "#37474F", False),
    "rain":    ("#16305C", "#3C6EA8", "#EAF4FF", "#7DD3FC", True),
    "snow":    ("#9CCBF5", "#F0F8FF", "#0B3C6E", "#0369A1", False),
    "storm":   ("#150C2E", "#4B2A7B", "#F3E8FF", "#C084FC", True),
    "night":   ("#0A0F2C", "#27346B", "#E8ECFF", "#93C5FD", True),
    "default": ("#1F2937", "#374151", "#F3F4F6", "#60A5FA", True),
}

# weather code: (description, emoji, theme)
WEATHER_CODES = {
    0: ("Clear sky", "☀️", "clear"),
    1: ("Mainly clear", "🌤️", "clear"),
    2: ("Partly cloudy", "⛅", "partly"),
    3: ("Overcast", "☁️", "cloudy"),
    45: ("Fog", "🌫️", "fog"),
    48: ("Rime fog", "🌫️", "fog"),
    51: ("Light drizzle", "🌦️", "rain"),
    53: ("Drizzle", "🌦️", "rain"),
    55: ("Heavy drizzle", "🌧️", "rain"),
    56: ("Freezing drizzle", "🌧️", "rain"),
    57: ("Freezing drizzle", "🌧️", "rain"),
    61: ("Light rain", "🌧️", "rain"),
    63: ("Rain", "🌧️", "rain"),
    65: ("Heavy rain", "🌧️", "rain"),
    66: ("Freezing rain", "🌧️", "rain"),
    67: ("Freezing rain", "🌧️", "rain"),
    71: ("Light snow", "🌨️", "snow"),
    73: ("Snow", "❄️", "snow"),
    75: ("Heavy snow", "❄️", "snow"),
    77: ("Snow grains", "❄️", "snow"),
    80: ("Light showers", "🌦️", "rain"),
    81: ("Rain showers", "🌧️", "rain"),
    82: ("Violent showers", "🌧️", "rain"),
    85: ("Snow showers", "🌨️", "snow"),
    86: ("Heavy snow showers", "🌨️", "snow"),
    95: ("Thunderstorm", "⛈️", "storm"),
    96: ("Thunderstorm, hail", "⛈️", "storm"),
    99: ("Thunderstorm, heavy hail", "⛈️", "storm"),
}

DIRECTIONS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


# =====================================================================
# Helper functions
# =====================================================================
def get_coordinates(city):
    """City name -> (latitude, longitude, name, country). Returns None if not found."""
    r = requests.get(GEO_URL, params={"name": city, "count": 1, "language": "en"}, timeout=10)
    r.raise_for_status()
    results = r.json().get("results")
    if not results:
        return None
    p = results[0]
    return p["latitude"], p["longitude"], p["name"], p.get("country", "")


def get_weather(lat, lon, unit):
    """Download current, hourly and 5-day weather data (JSON -> Python dictionary)."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,"
                   "weather_code,wind_speed_10m,wind_direction_10m,is_day",
        "hourly": "temperature_2m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                 "precipitation_sum,precipitation_probability_max",
        "timezone": "auto",
        "forecast_days": 5,
        "temperature_unit": "celsius" if unit == "C" else "fahrenheit",
        "wind_speed_unit": "kmh",
    }
    r = requests.get(WEATHER_URL, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def weather_info(code, is_day=1):
    """Weather code -> (description, emoji, theme name)."""
    desc, emoji, theme = WEATHER_CODES.get(code, ("Unknown", "🌡️", "default"))
    if is_day == 0 and theme in ("clear", "partly"):
        theme = "night"
        emoji = "🌙" if code in (0, 1) else "☁️"
    return desc, emoji, theme


def get_recommendation(theme, temp_c, wind, rain_chance):
    if theme == "storm":
        return "⚠️ Thunderstorm risk. Stay indoors."
    if theme == "rain" or rain_chance >= 60:
        return "☔ Take an umbrella with you."
    if theme == "snow":
        return "🧥 Snowy. Dress warmly."
    if wind >= 40:
        return "💨 Very windy. Be careful outside."
    if temp_c >= 38:
        return "🥵 Very hot. Drink lots of water."
    if temp_c <= 5:
        return "🧣 Cold day. Wear a jacket."
    return "✅ Good day for outdoor activity!"


def num(value, decimals=0, suffix=""):
    """Format a number safely (missing data -> N/A)."""
    if value is None:
        return "N/A"
    return f"{value:.{decimals}f}{suffix}"


def wind_direction(deg):
    if deg is None:
        return ""
    return DIRECTIONS[round(deg / 45) % 8]


def render(html_text):
    """Show HTML. Lines are joined so Markdown never treats it as a code block."""
    st.markdown("".join(line.strip() for line in html_text.splitlines()), unsafe_allow_html=True)


# =====================================================================
# Styling (colours change with the weather)
# =====================================================================
BASE_CSS = """
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {display:none !important;}
header[data-testid="stHeader"] {background: transparent !important;}
.stApp {background: linear-gradient(135deg, var(--c1), var(--c2)); background-attachment: fixed;}
.block-container {max-width: 1180px; padding-top: 2rem; padding-bottom: 3rem;}

.stApp label, .stApp [data-testid="stWidgetLabel"] p, .stApp [data-testid="stRadio"] *,
.stApp [data-testid="stCaptionContainer"] * {color: var(--fg) !important;}

div[data-baseweb="input"], div[data-baseweb="base-input"] {
    background: #ffffff !important; border-radius: 16px !important; border: none !important;
}
div[data-baseweb="input"] {box-shadow: 0 8px 24px rgba(0,0,0,0.18);}
div[data-baseweb="input"] input {
    color: #111111 !important; -webkit-text-fill-color: #111111 !important;
    font-size: 1.05rem; padding: 0.75rem 1rem;
}
[data-testid="stForm"] {border: none !important; padding: 0 !important; background: transparent !important;}

.stButton > button, [data-testid="stFormSubmitButton"] > button {
    width: 100%; border-radius: 999px; border: 1px solid var(--line);
    background: var(--glass); color: var(--fg); font-weight: 600;
    padding: 0.55rem 0.8rem; transition: all 0.2s ease;
}
.stButton > button p, [data-testid="stFormSubmitButton"] > button p {color: var(--fg) !important;}
.stButton > button:hover {transform: translateY(-2px); background: var(--glass2); border-color: var(--fg);}
[data-testid="stFormSubmitButton"] > button {
    background: var(--fg); height: 3.1rem; box-shadow: 0 8px 24px rgba(0,0,0,0.18);
}
[data-testid="stFormSubmitButton"] > button p {color: var(--c1) !important; font-weight: 800;}

.title {font-size: 2.4rem; font-weight: 800; color: var(--fg); letter-spacing: -0.5px;}
.subtitle {color: var(--fg); opacity: 0.75; margin-bottom: 1.2rem;}
.mini {font-size: 0.85rem; font-weight: 700; color: var(--fg); opacity: 0.85; margin: 0.9rem 0 0.3rem;}
.sec {font-size: 1.3rem; font-weight: 800; color: var(--fg); margin: 1.8rem 0 0.8rem;}
.foot {text-align: center; color: var(--fg); opacity: 0.65; font-size: 0.85rem; margin-top: 2rem;}

.hero {display: grid; grid-template-columns: 1fr 1.25fr; gap: 24px; padding: 28px;
    border-radius: 28px; background: var(--glass); border: 1px solid var(--line);
    box-shadow: 0 20px 50px rgba(0,0,0,0.18); backdrop-filter: blur(14px); color: var(--fg);
    margin-top: 1.2rem;}
.loc {font-size: 1.6rem; font-weight: 800;}
.when {opacity: 0.75; font-size: 0.95rem; margin-bottom: 12px;}
.bigrow {display: flex; align-items: center; gap: 14px;}
.bigemoji {font-size: 4.2rem;}
.bigtemp {font-size: 4.6rem; font-weight: 800; line-height: 1;}
.cond {font-size: 1.4rem; font-weight: 700; margin-top: 8px;}
.feels {opacity: 0.8; margin-top: 2px;}
.reco {display: inline-block; margin-top: 16px; padding: 9px 18px; border-radius: 999px;
    background: var(--glass2); border: 1px solid var(--line); font-weight: 700;}

.tiles {display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px;}
.tile {background: var(--glass2); border: 1px solid var(--line); border-radius: 20px; padding: 16px;
    transition: transform 0.2s ease;}
.tile:hover {transform: translateY(-4px);}
.t-ico {font-size: 1.4rem;}
.t-lab {font-size: 0.75rem; opacity: 0.75; text-transform: uppercase; letter-spacing: 0.7px; margin-top: 4px;}
.t-val {font-size: 1.7rem; font-weight: 800; margin-top: 2px;}
.t-sub {font-size: 0.8rem; opacity: 0.75; margin-top: 2px; min-height: 1.1em;}
.bar {height: 6px; border-radius: 99px; background: var(--line); margin-top: 8px; overflow: hidden;}
.bar > div {height: 100%; border-radius: 99px; background: var(--accent);}

.fgrid {display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px;}
.fc {text-align: center; padding: 20px 12px; border-radius: 24px; background: var(--glass);
    border: 1px solid var(--line); color: var(--fg); transition: all 0.25s ease;
    box-shadow: 0 10px 30px rgba(0,0,0,0.10);}
.fc:hover {transform: translateY(-8px); background: var(--glass2);}
.fc.today {border: 2px solid var(--accent);}
.fc-day {font-weight: 800; font-size: 1.1rem;}
.fc-date {opacity: 0.7; font-size: 0.8rem;}
.fc-ico {font-size: 2.8rem; margin: 10px 0 2px;}
.fc-desc {font-size: 0.85rem; opacity: 0.85; min-height: 2.4em;}
.fc-temps {font-weight: 700; margin-top: 8px;}
.range {position: relative; height: 6px; border-radius: 99px; background: var(--line); margin: 10px 6px;}
.range > div {position: absolute; top: 0; height: 100%; border-radius: 99px; background: var(--accent);}
.fc-rain {font-size: 0.85rem; margin-top: 8px;}

.msg {text-align: center; padding: 50px 20px; border-radius: 28px; background: var(--glass);
    border: 1px solid var(--line); color: var(--fg); margin-top: 1.5rem;}
.msg-ico {font-size: 3.6rem;}
.msg-title {font-size: 1.7rem; font-weight: 800; margin-top: 6px;}
.msg-text {opacity: 0.8; margin-top: 6px;}

[class*="st-key-card_"] {background: var(--glass); border: 1px solid var(--line); border-radius: 24px;
    padding: 18px 20px 10px; backdrop-filter: blur(12px); box-shadow: 0 10px 30px rgba(0,0,0,0.10);}
.card-title {font-weight: 800; font-size: 1.05rem; color: var(--fg); margin-bottom: 6px;}

@media (max-width: 900px) {
    .hero {grid-template-columns: 1fr;}
    .tiles {grid-template-columns: repeat(2, 1fr);}
    .fgrid {grid-template-columns: repeat(2, 1fr);}
}
"""


def apply_theme(theme_name):
    c1, c2, fg, accent, dark = THEMES[theme_name]
    glass = "rgba(255,255,255,0.10)" if dark else "rgba(255,255,255,0.40)"
    glass2 = "rgba(255,255,255,0.18)" if dark else "rgba(255,255,255,0.62)"
    line = "rgba(255,255,255,0.22)" if dark else "rgba(0,0,0,0.12)"
    root = (f":root{{--c1:{c1};--c2:{c2};--fg:{fg};--accent:{accent};"
            f"--glass:{glass};--glass2:{glass2};--line:{line};}}")
    render("<style>" + root + BASE_CSS + "</style>")


def message_card(icon, title, text):
    render(f"""
    <div class="msg">
        <div class="msg-ico">{icon}</div>
        <div class="msg-title">{title}</div>
        <div class="msg-text">{text}</div>
    </div>
    """)


def tile(icon, label, value, sub="", bar=None):
    bar_html = ""
    if bar is not None:
        bar_html = f'<div class="bar"><div style="width:{min(max(bar, 0), 100)}%"></div></div>'
    return (f'<div class="tile"><div class="t-ico">{icon}</div><div class="t-lab">{label}</div>'
            f'<div class="t-val">{value}</div><div class="t-sub">{sub}</div>{bar_html}</div>')


# =====================================================================
# Charts (Altair comes with Streamlit, nothing extra to install)
# =====================================================================
def show_chart(chart, fg, height=280):
    chart = chart.properties(height=height).configure(
        background="transparent",
        view={"strokeWidth": 0},
        axis={"labelColor": fg, "titleColor": fg, "gridColor": fg, "gridOpacity": 0.15,
              "domain": False, "ticks": False, "labelFontSize": 12, "titleFontSize": 12},
    )
    try:
        st.altair_chart(chart, width="stretch", theme=None)
    except TypeError:                      # older Streamlit versions
        st.altair_chart(chart, use_container_width=True, theme=None)


# =====================================================================
# Session state (remembers city and recent searches)
# =====================================================================
if "city" not in st.session_state:
    st.session_state.city = "Islamabad"
if "city_input" not in st.session_state:
    st.session_state.city_input = "Islamabad"
if "recent" not in st.session_state:
    st.session_state.recent = []


def search_city():
    st.session_state.city = st.session_state.city_input.strip()


def pick_city(city_name):
    st.session_state.city = city_name
    st.session_state.city_input = city_name


# =====================================================================
# 1) Get the data first (so the page colours can match the weather)
# =====================================================================
city = st.session_state.city
unit = "F" if st.session_state.get("unit_choice") == "°F" else "C"

status = "ok"
data = None
place = None

if city == "":
    status = "empty"
else:
    try:
        place = get_coordinates(city)
        if place is None:
            status = "notfound"
        else:
            data = get_weather(place[0], place[1], unit)
            _ = (data["current"], data["daily"], data["hourly"])   # check data is complete
    except requests.exceptions.RequestException:
        status = "network"
    except (KeyError, IndexError, ValueError, TypeError):
        status = "data"

theme_name = "default"
if status == "ok":
    cur = data["current"]
    desc, emoji, theme_name = weather_info(cur.get("weather_code"), cur.get("is_day", 1))
    # remember the search (most recent first, maximum 5)
    found_name = place[2]
    st.session_state.recent = ([found_name] +
                               [c for c in st.session_state.recent if c != found_name])[:5]

apply_theme(theme_name)
fg_color = THEMES[theme_name][2]
accent = THEMES[theme_name][3]

# =====================================================================
# 2) Header + search bar
# =====================================================================
render("""
<div class="title">🌤️ Weather Dashboard</div>
<div class="subtitle">Live weather, 5-day forecast and charts for any city in the world</div>
""")

with st.form("search_form"):
    box, button = st.columns([6, 1])
    box.text_input("City", key="city_input", placeholder="🔍  Search for a city, e.g. London",
                   label_visibility="collapsed")
    button.form_submit_button("Search", on_click=search_city)

opt1, opt2, _space = st.columns([1.6, 1.4, 5])
opt1.radio("Unit", ["°C", "°F"], horizontal=True, key="unit_choice", label_visibility="collapsed")
opt2.button("🔄 Refresh", key="refresh")          # a click reruns the script = fresh data

render('<div class="mini">🔥 Popular cities</div>')
pop_cols = st.columns(len(POPULAR_CITIES))
for col, name in zip(pop_cols, POPULAR_CITIES):
    col.button(name, key=f"pop_{name}", on_click=pick_city, args=(name,))

render('<div class="mini">🕘 Recent searches</div>')
if st.session_state.recent:
    rec_cols = st.columns(len(POPULAR_CITIES))
    for col, name in zip(rec_cols, st.session_state.recent):
        col.button(name, key=f"rec_{name}", on_click=pick_city, args=(name,))
else:
    st.caption("No searches yet.")

# =====================================================================
# 3) Messages for empty box / wrong city / problems
# =====================================================================
if status == "empty":
    message_card("✍️", "Enter a city", "Type a city name in the search box above and press Search.")
    st.stop()
if status == "notfound":
    message_card("🔍", "City not found",
                 f"We could not find “{escape(city)}”. Please check the spelling and try again.")
    st.stop()
if status == "network":
    message_card("📡", "Connection problem",
                 "Could not reach the weather service. Check your internet and press Refresh.")
    st.stop()
if status == "data":
    message_card("⚠️", "Weather data unavailable", "The data received was incomplete. Please try again.")
    st.stop()

# =====================================================================
# 4) Current weather
# =====================================================================
daily = data["daily"]
hourly = data["hourly"]
name, country = place[2], place[3]

temp = cur.get("temperature_2m")
feels = cur.get("apparent_temperature")
humidity = cur.get("relative_humidity_2m")
wind = cur.get("wind_speed_10m")
wind_dir = cur.get("wind_direction_10m")
rain_now = cur.get("precipitation")

highs = daily["temperature_2m_max"]
lows = daily["temperature_2m_min"]
rain_probs = [p if p is not None else 0 for p in daily["precipitation_probability_max"]]
rain_sums = daily["precipitation_sum"]
days = daily["time"]

temp_c = 20 if temp is None else (temp if unit == "C" else (temp - 32) * 5 / 9)
reco = get_recommendation(theme_name, temp_c, wind or 0, rain_probs[0])
when = pd.to_datetime(cur["time"]).strftime("%A, %d %B %Y  •  %H:%M")

tiles_html = (
    tile("💧", "Humidity", num(humidity, 0, "%"), "Moisture in the air", humidity or 0)
    + tile("💨", "Wind", num(wind, 0, " km/h"), f"Direction: {wind_direction(wind_dir) or 'N/A'}")
    + tile("🌧️", "Rain now", num(rain_now, 1, " mm"), f"Today total: {num(rain_sums[0], 1, ' mm')}")
    + tile("☔", "Rain chance", f"{rain_probs[0]}%", "Probability today", rain_probs[0])
    + tile("🔺", "Highest", num(highs[0], 0, f"°{unit}"), "Today")
    + tile("🔻", "Lowest", num(lows[0], 0, f"°{unit}"), "Today")
)

render(f"""
<div class="hero">
    <div>
        <div class="loc">📍 {escape(name)}, {escape(country)}</div>
        <div class="when">{when}</div>
        <div class="bigrow">
            <div class="bigemoji">{emoji}</div>
            <div class="bigtemp">{num(temp, 0, f"°{unit}")}</div>
        </div>
        <div class="cond">{desc}</div>
        <div class="feels">Feels like {num(feels, 0, f"°{unit}")}</div>
        <div class="reco">{reco}</div>
    </div>
    <div class="tiles">{tiles_html}</div>
</div>
""")

# =====================================================================
# 5) 5-day forecast cards
# =====================================================================
render('<div class="sec">📅 5-Day Forecast</div>')

known_lows = [x for x in lows if x is not None] or [0]
known_highs = [x for x in highs if x is not None] or [0]
week_min, week_max = min(known_lows), max(known_highs)
span = max(week_max - week_min, 1)

cards = ""
for i in range(len(days)):
    d = pd.to_datetime(days[i])
    f_desc, f_emoji, _ = weather_info(daily["weather_code"][i], 1)
    hi = highs[i] if highs[i] is not None else week_max
    lo = lows[i] if lows[i] is not None else week_min
    left = (lo - week_min) / span * 100
    width = max((hi - lo) / span * 100, 8)
    label = "Today" if i == 0 else d.strftime("%A")[:3]
    today_class = " today" if i == 0 else ""
    cards += f"""
    <div class="fc{today_class}">
        <div class="fc-day">{label}</div>
        <div class="fc-date">{d.strftime("%d %b")}</div>
        <div class="fc-ico">{f_emoji}</div>
        <div class="fc-desc">{f_desc}</div>
        <div class="fc-temps">{num(highs[i], 0, "°")} / {num(lows[i], 0, "°")}</div>
        <div class="range"><div style="left:{left}%;width:{width}%"></div></div>
        <div class="fc-rain">💧 {rain_probs[i]}% &nbsp;•&nbsp; {num(rain_sums[i], 1, " mm")}</div>
    </div>
    """
render(f'<div class="fgrid">{cards}</div>')

# =====================================================================
# 6) Charts (three different types)
# =====================================================================
render('<div class="sec">📊 Charts</div>')

# ---- Chart 1: next 24 hours temperature (area chart) ----
times = hourly["time"]
temps = hourly["temperature_2m"]
now_hour = cur["time"][:13]
start = next((i for i, t in enumerate(times) if t[:13] >= now_hour), 0)
hour_df = pd.DataFrame({
    "Time": pd.to_datetime(times[start:start + 24]),
    "Temp": temps[start:start + 24],
})

with st.container(key="card_temp"):
    render('<div class="card-title">🌡️ Temperature - next 24 hours</div>')
    base = alt.Chart(hour_df).encode(
        x=alt.X("Time:T", title=None, axis=alt.Axis(format="%H:%M", labelAngle=0, tickCount=8)),
        y=alt.Y("Temp:Q", title=f"°{unit}", scale=alt.Scale(zero=False)),
    )
    area = base.mark_area(
        interpolate="monotone",
        line={"color": accent, "strokeWidth": 3},
        color=alt.Gradient(
            gradient="linear",
            stops=[alt.GradientStop(color="rgba(255,255,255,0)", offset=0),
                   alt.GradientStop(color=accent, offset=1)],
            x1=1, x2=1, y1=1, y2=0),
    )
    points = base.mark_point(filled=True, size=55, color=accent, opacity=1).encode(
        tooltip=[alt.Tooltip("Time:T", title="Time", format="%H:%M"),
                 alt.Tooltip("Temp:Q", title="Temperature", format=".1f")])
    show_chart(area + points, fg_color, 300)

col_a, col_b = st.columns(2)

# ---- Chart 2: daily low-to-high range (floating bars) ----
labels = [("Today" if i == 0 else pd.to_datetime(d).strftime("%a")) for i, d in enumerate(days)]
range_df = pd.DataFrame({"Day": labels, "Low": lows, "High": highs})
y_scale = alt.Scale(domain=[week_min - 4, week_max + 4])

with col_a:
    with st.container(key="card_range"):
        render('<div class="card-title">↕️ Daily low and high</div>')
        base = alt.Chart(range_df).encode(
            x=alt.X("Day:N", sort=None, title=None, axis=alt.Axis(labelAngle=0)))
        bars = base.mark_bar(cornerRadius=12, size=28, color=accent, opacity=0.9).encode(
            y=alt.Y("Low:Q", scale=y_scale, title=f"°{unit}"),
            y2="High:Q",
            tooltip=["Day:N", "Low:Q", "High:Q"])
        top = base.mark_text(dy=-12, fontWeight="bold", fontSize=13, color=fg_color).encode(
            y=alt.Y("High:Q", scale=y_scale, axis=None), text=alt.Text("High:Q", format=".0f"))
        bottom = base.mark_text(dy=14, fontWeight="bold", fontSize=13, color=fg_color).encode(
            y=alt.Y("Low:Q", scale=y_scale, axis=None), text=alt.Text("Low:Q", format=".0f"))
        show_chart(bars + top + bottom, fg_color, 300)

# ---- Chart 3: rain probability (lollipop chart) ----
rain_df = pd.DataFrame({"Day": labels, "Rain": rain_probs, "Zero": 0})
rain_scale = alt.Scale(domain=[0, 120])

with col_b:
    with st.container(key="card_rain"):
        render('<div class="card-title">☔ Chance of rain</div>')
        base = alt.Chart(rain_df).encode(
            x=alt.X("Day:N", sort=None, title=None, axis=alt.Axis(labelAngle=0)))
        stick = base.mark_rule(strokeWidth=5, strokeCap="round", color=accent, opacity=0.55).encode(
            y=alt.Y("Zero:Q", scale=rain_scale, title="%"), y2="Rain:Q")
        dot = base.mark_circle(size=380, color=accent, opacity=1).encode(
            y=alt.Y("Rain:Q", scale=rain_scale, axis=None),
            tooltip=["Day:N", alt.Tooltip("Rain:Q", title="Rain chance %")])
        text = base.mark_text(dy=-24, fontWeight="bold", fontSize=13, color=fg_color).encode(
            y=alt.Y("Rain:Q", scale=rain_scale, axis=None), text=alt.Text("Rain:Q", format=".0f"))
        show_chart(stick + dot + text, fg_color, 300)

render('<div class="foot">Weather data by Open-Meteo.com</div>')