# Configuration settings for OneDrive to PI sync script
import os

# OneDrive Folder / File Path Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def find_onedrive_folder() -> str:
    """Dynamically locates the OneDrive Log Book folder."""
    # Look for any OneDrive_* directory inside onedrive_to_pi
    for entry in sorted(os.listdir(BASE_DIR), reverse=True):
        full_p = os.path.join(BASE_DIR, entry)
        if os.path.isdir(full_p) and entry.startswith("OneDrive_"):
            # Check for subfolder containing Log book
            for sub in os.listdir(full_p):
                sub_p = os.path.join(full_p, sub)
                if os.path.isdir(sub_p) and "log book" in sub.lower():
                    return sub_p
            return full_p
    return os.path.join(BASE_DIR, "OneDrive_2026-08-26", "Log book Pulp Line 2 - 2026")

ONEDRIVE_PATH = find_onedrive_folder()
ONEDRIVE_FILE_PATH = ONEDRIVE_PATH  # Backward compatibility

# State Management Configuration
SYNC_STATE_FILE = os.path.join(BASE_DIR, "sync_state.json")
SAVE_STATE = True  # Enable state tracking to send only new real-time lab updates

# Excel Sheet Structure Settings for Line 2 Log Book
EXCEL_DATA_START_ROW = 7   # 1-based row index where hourly data begins (Row 7 in Excel)
EXCEL_DATA_END_ROW = 30     # Approximate end row for 24-hour log
DATE_CELL = (4, 1)          # (Row 4, Col B) 0-indexed: row 3, col 1 -> '01-08-26'

# Column Indices (0-indexed where Col A = 0, Col B = 1, Col C = 2...)
COL_TIME = 1        # Col B: Time ("8:00 AM", "9:00 AM", ...)
COL_KAPPA_PRESS1 = 5 # Col F: Kappa Press 1
COL_KAPPA_PRESS3 = 6 # Col G: Kappa Press 3
COL_KAPPA_EOP = 7    # Col H: Kappa Eop

COL_VISC_PRESS1 = 8  # Col I: Viscosity Press 1
COL_VISC_PRESS3 = 9  # Col J: Viscosity Press 3
COL_VISC_D0 = 10     # Col K: Viscosity D0
COL_VISC_EOP = 11    # Col L: Viscosity Eop
COL_VISC_D1 = 12     # Col M: Viscosity D1
COL_VISC_D2 = 13     # Col N: Viscosity D2

COL_BRIGHT_PRESS1 = 15 # Col P: Brightness Press 1
COL_BRIGHT_PRESS3 = 16 # Col Q: Brightness Press 3
COL_BRIGHT_D0 = 17     # Col R: Brightness D0
COL_BRIGHT_EOP = 18    # Col S: Brightness Eop
COL_BRIGHT_D1 = 19     # Col T: Brightness D1
COL_BRIGHT_D2 = 21     # Col V: Brightness D2

COL_PH_D0 = 26         # Col AA: pH D0
COL_PH_EOP = 27        # Col AB: pH Eop
COL_PH_D1 = 28         # Col AC: pH D1
COL_PH_D2 = 29         # Col AD: pH D2

# Historical PI Write API Configuration (Local Gateway app_pro on port 5707)
WRITE_OLD_API_URL = "http://127.0.0.1:5707/write_old"
WRITE_OLD_API_TOKEN = "A9r2T8#kZp2@Vxg9!QwLm4&FjN7Yc$HPs3B5eUaDS1G0oXmIQpqz0Oo8LI"

# MI Cube API Configuration (Fallback)
MI_CUBE_API_URL = "https://micube.scg.com/v2/api/Datacenter/PIServer/WriteValue/ByTag/"
API_TOKEN = "76ED1A0F-7386-432B-B586-5A8304AE20FB"

PI_SERVER_NAME = "VPKGDRBPPI01"

# PI Tag Mapping for Line 2 Lab Data
PI_TAG_MAPPING = {
    # Kappa
    "Kappa_Press1": "PULP-LINE2-KAPPA-PRESS1",
    "Kappa_Press3": "PULP-LINE2-KAPPA-PRESS3",
    "Kappa_Eop": "PULP-LINE2-KAPPA-EOP",
    # Viscosity
    "Viscosity_Press1": "PULP-LINE2-VISCOSITY-PRESS1",
    "Viscosity_Press3": "PULP-LINE2-VISCOSITY-PRESS3",
    "Viscosity_D0": "PULP-LINE2-VISCOSITY-D0",
    "Viscosity_Eop": "PULP-LINE2-VISCOSITY-EOP",
    "Viscosity_D1": "PULP-LINE2-VISCOSITY-D1",
    "Viscosity_D2": "PULP-LINE2-VISCOSITY-D2",
    # Brightness
    "Brightness_Press1": "PULP-LINE2-BRIGHTNESS-PRESS1",
    "Brightness_Press3": "PULP-LINE2-BRIGHTNESS-PRESS3",
    "Brightness_D0": "PULP-LINE2-BRIGHTNESS-D0",
    "Brightness_Eop": "PULP-LINE2-BRIGHTNESS-EOP",
    "Brightness_D1": "PULP-LINE2-BRIGHTNESS-D1",
    "Brightness_D2": "PULP-LINE2-BRIGHTNESS-D2",
    # pH
    "pH_D0": "PULP-LINE2-PH-D0",
    "pH_Eop": "PULP-LINE2-PH-EOP",
    "pH_D1": "PULP-LINE2-PH-D1",
    "pH_D2": "PULP-LINE2-PH-D2",
}
