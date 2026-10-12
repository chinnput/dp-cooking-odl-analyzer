# Tag cheat sheet

The full Thai table, with Excel columns, is in `DP Cooking ODL Analyzer/tag_summary.md`. The mapping in code is `onedrive_to_pi/config.py` → `PI_TAG_MAPPING` and the `COL_*` constants.

## Notebook tags (12, `TAGS` in realtime_pi_press1_analysis.ipynb)

| PI tag | Meaning | Unit |
|---|---|---|
| `PPPC_DP_Cooking.B1_Discharge_FinalTime_Press1_Status` … `B4_…` | Digester k's pulp at Press 1 (value k, otherwise 0; can be fractional) | flag |
| `PULP-LINE2-KAPPA-PRESS1` | Kappa at Press 1 (lab, every 4 h) | – |
| `PULP-LINE2-VISCOSITY-PRESS1` | Viscosity at Press 1 (lab, every 4 h) | cm³/g |
| `PULP-LINE2-BRIGHTNESS-PRESS1` | Brightness at Press 1 (lab, every 2 h) | % |
| `PM2.105FIC303:MV` | White Liquor to dilution screw | m³/h |
| `PM2.305FIC036:MV` | MP Steam, pulp heater before Reactor 2 | t/h |
| `PM2.Prod.ODL` | Production ODL | ADT/D |
| `PM2.105NIC207:MV` | Press 1 feed consistency | % |
| `PM2.106FIC006:MV` | Deknotting feed flow | m³/h |

## 19 lab tags written by onedrive_to_pi

Naming pattern: `PULP-LINE2-<PARAM>-<STAGE>`

- **Kappa:** PRESS1, PRESS3, EOP
- **Viscosity:** PRESS1, PRESS3, D0, EOP, D1, D2
- **Brightness:** PRESS1, PRESS3, D0, EOP, D1, D2
- **pH:** D0, EOP, D1, D2

Here D0/D1/D2 are **bleaching towers**, not digesters. Don't confuse them with digesters D1–D4.

Log book layout: data starts at row 7, time is in column B, and the date is in cell (row 4, col B). Each monthly file has one sheet per day of the month (`1`–`31`). Timestamps after midnight roll over to the next day.

## Pteam DCS feature names (31, from the Excel export)

Production and flow, chemicals and steam, ODL reactor temperature and pressure, 4 specific consumptions (`Specific Steam Consumption (t_ADT)` and others), and the status triggers `DigN_Discharge_BatchStatus` / `DigN_Press1_BatchStatus`. The full list is in `tag_summary.md` sections 2.1–2.5.
