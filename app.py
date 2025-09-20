import streamlit as st
import pandas as pd
import requests
from math import radians, sin, cos, sqrt, atan2
import concurrent.futures

# ✅ LocationIQ API Key
LOCATIONIQ_KEY = "pk.3f010bc1f26e7b7b2d1e991e4c8f67d5"

# Set up page
st.set_page_config(page_title="📍 Pincode Distance Finder", layout="wide")
st.title("📍 Pincode-to-Pincode Distance Finder")

# ✅ Load Fallback Pincode File Once
@st.cache_data(show_spinner=False)
def load_fallback_data():
    try:
        df = pd.read_csv(r"D:\Tools\Pincode To Pincode\Pincode 11list.csv", dtype=str)
        df.columns = [col.strip().lower() for col in df.columns]
        return df.set_index("pincode").to_dict(orient="index")
    except Exception as e:
        st.error(f"❌ Failed to load fallback file: {e}")
        return {}

PINCODE_LOOKUP = load_fallback_data()

# ✅ Get City/District/State from India Post
@st.cache_data(show_spinner=False)
def get_location(pincode):
    try:
        res = requests.get(f"https://api.postalpincode.in/pincode/{pincode}", timeout=5)
        data = res.json()
        if data[0]['Status'] == 'Success':
            office = data[0]['PostOffice'][0]
            return {
                "City": office.get("Name", "N/A"),
                "District": office.get("District", "N/A"),
                "State": office.get("State", "N/A")
            }
    except:
        pass
    return {"City": "N/A", "District": "N/A", "State": "N/A"}

# ✅ Get Latitude/Longitude from LocationIQ
@st.cache_data(show_spinner=False)
def get_lat_lon(pincode):
    try:
        url = f"https://us1.locationiq.com/v1/search.php?key={LOCATIONIQ_KEY}&postalcode={pincode}&country=India&format=json"
        res = requests.get(url, timeout=10)
        data = res.json()
        if isinstance(data, list) and len(data) > 0:
            lat = float(data[0]['lat'])
            lon = float(data[0]['lon'])
            return lat, lon
    except Exception as e:
        print(f"Lat/Lon error for {pincode}: {e}")
    return None, None

# ✅ Haversine Distance Calculation
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    return round(R * 2 * atan2(sqrt(a), sqrt(1 - a)), 2)

# ✅ Metro Pincode Ranges
METRO_PINCODE_RANGES = [
    range(110001, 110099),  # New Delhi
    range(400001, 400105),  # Mumbai
    range(700001, 700105),  # Kolkata
    range(600001, 600119),  # Chennai
    range(560001, 560108),  # Bengaluru
    range(500001, 500099),  # Hyderabad
    range(380001, 380062),  # Ahmedabad
    range(411001, 411063),  # Pune
    range(122001, 122019)   # Gurgaon
]

def is_metro_pincode(pin):
    try:
        p = int(pin)
        return any(p in r for r in METRO_PINCODE_RANGES)
    except:
        return False

# ✅ Row-wise Processor
def process_row(row):
    from_pin = str(row['from_pincode']).strip()
    to_pin = str(row['to_pincode']).strip()

    # API Location
    from_loc = get_location(from_pin)
    to_loc = get_location(to_pin)

    # Fallback Lookup if API fails
    if from_loc['City'] == "N/A":
        from_fallback = PINCODE_LOOKUP.get(from_pin, {})
        from_loc['City'] = from_fallback.get('city', "N/A")
        from_loc['District'] = from_fallback.get('district', "N/A")
        from_loc['State'] = from_fallback.get('state', "N/A")

    if to_loc['City'] == "N/A":
        to_fallback = PINCODE_LOOKUP.get(to_pin, {})
        to_loc['City'] = to_fallback.get('city', "N/A")
        to_loc['District'] = to_fallback.get('district', "N/A")
        to_loc['State'] = to_fallback.get('state', "N/A")

    # Coordinates
    from_lat, from_lon = get_lat_lon(from_pin)
    to_lat, to_lon = get_lat_lon(to_pin)

    if from_lat is None or to_lat is None or from_lon is None or to_lon is None:
        distance_km = "#N/A"
    else:
        distance_km = haversine(from_lat, from_lon, to_lat, to_lon)

    # Zone Classification
    from_district = from_loc['District'].strip().lower()
    to_district = to_loc['District'].strip().lower()
    from_state = from_loc['State'].strip().lower()
    to_state = to_loc['State'].strip().lower()

    special_states = {
        "himachal pradesh", "karnataka", "jammu & kashmir", "west bengal", "assam", 
        "manipur", "mizoram", "nagaland", "tripura", "meghalaya", "sikkim", "arunachal pradesh"
    }

    if from_pin == to_pin:
        zone = "LOCAL"
    elif from_district == to_district and from_district != "n/a":
        zone = "LOCAL"
    elif is_metro_pincode(from_pin) and is_metro_pincode(to_pin):
        zone = "METRO"
    elif from_state == to_state and from_state != "n/a":
        zone = "REGIONAL"
    elif from_state in special_states or to_state in special_states:
        zone = "SPECIAL"
    else:
        zone = "ROI"

    result = {
        "From Pincode": from_pin,
        "To Pincode": to_pin,
        "From City": from_loc['City'],
        "From District": from_loc['District'],
        "From State": from_loc['State'],
        "To City": to_loc['City'],
        "To District": to_loc['District'],
        "To State": to_loc['State'],
        "Distance (KM)": "",
        "Zone": zone
    }

    if isinstance(distance_km, (int, float)):
        result["Distance (KM)"] = distance_km

    return result

# ---------------- UI -------------------
tab1, tab2 = st.tabs(["📄 Upload File", "✍️ Manual Search"])

with tab1:
    file = st.file_uploader("Upload CSV or Excel with `from_pincode` and `to_pincode` columns", type=["csv", "xlsx"])
    if file:
        df = pd.read_csv(file) if file.name.endswith(".csv") else pd.read_excel(file)
        if 'from_pincode' in df.columns and 'to_pincode' in df.columns:
            st.success(f"✅ {len(df)} rows detected. Processing...")
            with st.spinner("Fetching city/state and calculating distance..."):
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    results = list(executor.map(process_row, df.to_dict('records')))
                result_df = pd.DataFrame(results)
                st.dataframe(result_df, use_container_width=True)

                csv = result_df.to_csv(index=False).encode('utf-8')
                st.download_button("📅 Download Results", csv, "pincode_distance_output.csv", "text/csv")
        else:
            st.error("❌ File must have 'from_pincode' and 'to_pincode' columns")

with tab2:
    col1, col2 = st.columns(2)
    from_pin = col1.text_input("From Pincode")
    to_pin = col2.text_input("To Pincode")

    if st.button("🔍 Get Distance"):
        if from_pin and to_pin:
            with st.spinner("Fetching info..."):
                result = process_row({'from_pincode': from_pin, 'to_pincode': to_pin})
                st.write(pd.DataFrame([result]))
        else:
            st.warning("⚠️ Enter both pincodes")