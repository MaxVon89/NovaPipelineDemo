import requests
import json
import os

MAST_URL = "https://mast.stsci.edu/api/v0/invoke"

# -------------------------------
# Helper: safe API call
# -------------------------------
def mast_query(payload):
    r = requests.post(MAST_URL, data={"request": json.dumps(payload)})
    result = r.json()

    if "status" in result and result["status"] == "error":
        raise Exception(f"MAST API Error: {result}")

    if "data" not in result:
        raise Exception(f"Unexpected response: {result}")

    return result["data"]


# -------------------------------
# Step 1: Get JWST observations
# -------------------------------
print("🔍 Querying JWST observations...")

obs_query = {
    "service": "Mast.Caom.Filtered",
    "params": {
        "columns": "obsid,instrument_name",
        "filters": [
            {"paramName": "obs_collection", "values": ["JWST"]}
        ]
    },
    "format": "json"
}

obs_data = mast_query(obs_query)

print(f"Total JWST observations: {len(obs_data)}")

# -------------------------------
# Step 2: Filter NIRCam
# -------------------------------
nircam_obs = [
    o for o in obs_data
    if "NIRCAM" in o["instrument_name"].upper()
]

print(f"NIRCam observations: {len(nircam_obs)}")

# -------------------------------
# Step 3: Find uncal products
# -------------------------------
all_uncal = []

for obs in nircam_obs[:5]:   # LIMIT for safety
    obsid = obs["obsid"]

    prod_query = {
        "service": "Mast.Caom.Products",
        "params": {
            "obsid": obsid,
            "columns": "*"
        },
        "format": "json"
    }

    products = mast_query(prod_query)

    # Debug: print sample filenames
    for p in products[:3]:
        print("   ↳", p.get("productFilename"), p.get("calib_level"))

    # Filter true raw files
    uncal = [
        p for p in products
        if "uncal" in p.get("productFilename", "").lower()
    ]

    print(f"obsid {obsid} → {len(uncal)} uncal files")

    all_uncal.extend(uncal)

print(f"\nTotal uncal files found: {len(all_uncal)}")

# -------------------------------
# Step 4: Download
# -------------------------------
DATA_DIR = "/tmp/data"
os.makedirs(DATA_DIR, exist_ok=True)

def download(uri):
    url = f"https://mast.stsci.edu/api/v0.1/Download/file?uri={uri}"
    filename = uri.split("/")[-1]
    path = os.path.join(DATA_DIR, filename)

    print(f"⬇️ Downloading {filename}...")

    r = requests.get(url, stream=True)

    if r.status_code != 200:
        print(f"❌ Failed: {filename}")
        return

    with open(path, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)

    print(f"✅ Saved: {path}")


# Download a few files only
for f in all_uncal[:3]:
    download(f["dataURI"])

print("\n🎉 Done. Check the 'data/' folder.")
