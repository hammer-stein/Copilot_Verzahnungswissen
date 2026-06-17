# Testergebnisse — CAD-Geometrie-Pipeline

**Datum:** 2026-06-16  
**Test:** `python cad_processor/tests/accuracy_test.py`  
**Schwellen:** OK ≤ 2 % · Warnung ≤ 5 % · Fehler > 5 % Abweichung  
**Datenquelle:** reale McMaster-Carr-STEP-Dateien, Soll aus Hersteller-Datenblättern  

## Gesamtergebnis: 276/286 Parameter korrekt (97%)  |  3 Warnungen  |  7 Fehler

## Übersicht je Datei

| Datei | Typ | Ergebnis |
|---|---|---|
| `2664N11_Metal Gear - 20 Degree Pressure Angle.STEP` | spur | 12/12 OK  (0 ⚠  0 ✗  0 ?) |
| `2664N19_Metal Gear - 20 Degree Pressure Angle.STEP` | spur | 13/13 OK  (0 ⚠  0 ✗  0 ?) |
| `2664N311_Metal Gear - 20 Degree Pressure Angle.STEP` | spur | 11/12 OK  (1 ⚠  0 ✗  0 ?) |
| `2664N486_Metal Gear - 20 Degree Pressure Angle.STEP` | spur | 13/13 OK  (0 ⚠  0 ✗  0 ?) |
| `2515N11_Metal Bevel Gear.STEP` | bevel | 12/12 OK  (0 ⚠  0 ✗  0 ?) |
| `2515N15_Metal Bevel Gear.STEP` | bevel | 12/12 OK  (0 ⚠  0 ✗  0 ?) |
| `2515N336_Metal Bevel Gear.STEP` | bevel | 10/12 OK  (2 ⚠  0 ✗  0 ?) |
| `2515N355_Metal Bevel Gear.STEP` | bevel | 12/12 OK  (0 ⚠  0 ✗  0 ?) |
| `3856N121_Plastic Bevel Gear.STEP` | bevel | 12/12 OK  (0 ⚠  0 ✗  0 ?) |
| `6010N13_High-Power Metal Bevel Gear.STEP` | bevel | 10/10 OK  (0 ⚠  0 ✗  0 ?) |
| `2600N14_Metal Miter Gear.STEP` | miter | 12/14 OK  (0 ⚠  0 ✗  2 ?) |
| `2600N15_Metal Miter Gear.STEP` | miter | 12/14 OK  (0 ⚠  0 ✗  2 ?) |
| `2600N5_Metal Miter Gear.STEP` | miter | 14/14 OK  (0 ⚠  0 ✗  0 ?) |
| `2810N2_Plastic Miter Gear.STEP` | miter | 12/12 OK  (0 ⚠  0 ✗  0 ?) |
| `3560N14_Metal Miter Gear.STEP` | miter | 14/14 OK  (0 ⚠  0 ✗  0 ?) |
| `6529K57_Metal Miter Gear.STEP` | miter | 9/9 OK  (0 ⚠  0 ✗  0 ?) |
| `6529K58_Metal Miter Gear.STEP` | miter | 14/14 OK  (0 ⚠  0 ✗  0 ?) |
| `6529K61_Metal Miter Gear.STEP` | miter | 14/14 OK  (0 ⚠  0 ✗  0 ?) |
| `2540N13_Plastic Ratcheting Gear.STEP` | ratchet | 7/7 OK  (0 ⚠  0 ✗  0 ?) |
| `6283K121_Metal Ratcheting Gear.STEP` | ratchet | 8/8 OK  (0 ⚠  0 ✗  0 ?) |
| `6283K12_Metal Ratcheting Gear.STEP` | ratchet | 7/7 OK  (0 ⚠  0 ✗  0 ?) |
| `6283K24_Metal Ratcheting Gear.STEP` | ratchet | 7/7 OK  (0 ⚠  0 ✗  0 ?) |
| `6283K62_Metal Ratcheting Gear.STEP` | ratchet | 3/3 OK  (0 ⚠  0 ✗  0 ?) |
| `6283K93_Metal Ratcheting Gear.STEP` | ratchet | 8/8 OK  (0 ⚠  0 ✗  0 ?) |
| `6283K94_Metal Ratcheting Gear.STEP` | ratchet | 8/8 OK  (0 ⚠  0 ✗  0 ?) |
| `6283K96_Metal Ratcheting Gear.STEP` | ratchet | 8/8 OK  (0 ⚠  0 ✗  0 ?) |
| `2485N205_Metal Gear Rack - 20 Degree Pressure Angle.STEP` | rack | 2/5 OK  (0 ⚠  3 ✗  0 ?) |

## Detail je Datei (Parameter-Abgleich)

### Stirnräder (spur)

#### `2664N11_Metal Gear - 20 Degree Pressure Angle.STEP`  
<sub>2664N11 · Black-Oxide 1045 Carbon Steel</sub>

| Status | Parameter | Messung / Vergleich |
|:--:|---|---|
| ✅ | `gear_type` | spur |
| ✅ | `is_internal_gear` | False |
| ✅ | `num_teeth` | 15 |
| ✅ | `module_mm` | 1.000  (erwartet: 1.000,  Δ=0.0%) |
| ✅ | `outer_diameter_mm` | 17.036  (erwartet: 17.000,  Δ=0.2%) |
| ✅ | `pitch_diameter_mm` | 15.000  (erwartet: 15.000,  Δ=0.0%) |
| ✅ | `root_diameter_mm` | 12.488  (erwartet: 12.500,  Δ=0.1%) |
| ✅ | `face_width_mm` | 10.004  (erwartet: 10.000,  Δ=0.0%) |
| ✅ | `helix_angle_deg` | 0.000  (erwartet: 0) |
| ✅ | `pressure_angle_deg` | 20.000  (erwartet: 20.000,  Δ=0.0%) |
| ✅ | `bore_diameter_mm` | 5.951  (erwartet: 6.000,  Δ=0.8%) |
| ✅ | `overall_width_mm` | 30.028  (erwartet: 30.000,  Δ=0.1%) |

**Ergebnis: 12/12 OK  (0 ⚠  0 ✗  0 ?)**

#### `2664N19_Metal Gear - 20 Degree Pressure Angle.STEP`  
<sub>2664N19 · Black-Oxide 1045 Carbon Steel</sub>

| Status | Parameter | Messung / Vergleich |
|:--:|---|---|
| ✅ | `gear_type` | spur |
| ✅ | `is_internal_gear` | False |
| ✅ | `num_teeth` | 36 |
| ✅ | `module_mm` | 1.500  (erwartet: 1.500,  Δ=0.0%) |
| ✅ | `outer_diameter_mm` | 57.062  (erwartet: 57.000,  Δ=0.1%) |
| ✅ | `pitch_diameter_mm` | 54.000  (erwartet: 54.000,  Δ=0.0%) |
| ✅ | `root_diameter_mm` | 50.186  (erwartet: 50.250,  Δ=0.1%) |
| ✅ | `face_width_mm` | 15.002  (erwartet: 15.000,  Δ=0.0%) |
| ✅ | `helix_angle_deg` | 0.000  (erwartet: 0) |
| ✅ | `pressure_angle_deg` | 20.000  (erwartet: 20.000,  Δ=0.0%) |
| ✅ | `bore_diameter_mm` | 11.943  (erwartet: 12.000,  Δ=0.5%) |
| ✅ | `overall_width_mm` | 25.029  (erwartet: 25.000,  Δ=0.1%) |
| ✅ | `hub_diameter_mm` | 40.000  (erwartet: 40.000,  Δ=0.0%) |

**Ergebnis: 13/13 OK  (0 ⚠  0 ✗  0 ?)**

#### `2664N311_Metal Gear - 20 Degree Pressure Angle.STEP`  
<sub>2664N311 · Black-Oxide 1045 Carbon Steel</sub>

| Status | Parameter | Messung / Vergleich |
|:--:|---|---|
| ✅ | `gear_type` | spur |
| ✅ | `is_internal_gear` | False |
| ✅ | `num_teeth` | 15 |
| ✅ | `module_mm` | 0.500  (erwartet: 0.500,  Δ=0.0%) |
| ✅ | `outer_diameter_mm` | 8.552  (erwartet: 8.500,  Δ=0.6%) |
| ✅ | `pitch_diameter_mm` | 7.500  (erwartet: 7.500,  Δ=0.0%) |
| ✅ | `root_diameter_mm` | 6.241  (erwartet: 6.250,  Δ=0.1%) |
| ✅ | `face_width_mm` | 5.005  (erwartet: 5.000,  Δ=0.1%) |
| ✅ | `helix_angle_deg` | 0.000  (erwartet: 0) |
| ✅ | `pressure_angle_deg` | 20.000  (erwartet: 20.000,  Δ=0.0%) |
| ⚠️ | `bore_diameter_mm` | 2.921  (erwartet: 3.000,  Δ=2.6%) |
| ✅ | `overall_width_mm` | 16.040  (erwartet: 16.000,  Δ=0.3%) |

**Ergebnis: 11/12 OK  (1 ⚠  0 ✗  0 ?)**

#### `2664N486_Metal Gear - 20 Degree Pressure Angle.STEP`  
<sub>2664N486 · Brass</sub>

| Status | Parameter | Messung / Vergleich |
|:--:|---|---|
| ✅ | `gear_type` | spur |
| ✅ | `is_internal_gear` | False |
| ✅ | `num_teeth` | 30 |
| ✅ | `module_mm` | 1.000  (erwartet: 1.000,  Δ=0.0%) |
| ✅ | `outer_diameter_mm` | 32.057  (erwartet: 32.000,  Δ=0.2%) |
| ✅ | `pitch_diameter_mm` | 30.000  (erwartet: 30.000,  Δ=0.0%) |
| ✅ | `root_diameter_mm` | 27.431  (erwartet: 27.500,  Δ=0.3%) |
| ✅ | `face_width_mm` | 6.003  (erwartet: 6.000,  Δ=0.0%) |
| ✅ | `helix_angle_deg` | 0.000  (erwartet: 0) |
| ✅ | `pressure_angle_deg` | 20.000  (erwartet: 20.000,  Δ=0.0%) |
| ✅ | `bore_diameter_mm` | 5.955  (erwartet: 6.000,  Δ=0.7%) |
| ✅ | `overall_width_mm` | 14.036  (erwartet: 14.000,  Δ=0.3%) |
| ✅ | `hub_diameter_mm` | 25.000  (erwartet: 25.000,  Δ=0.0%) |

**Ergebnis: 13/13 OK  (0 ⚠  0 ✗  0 ?)**

### Kegelräder (bevel)

#### `2515N11_Metal Bevel Gear.STEP`  
<sub>2515N11 · 1144 Carbon Steel</sub>

| Status | Parameter | Messung / Vergleich |
|:--:|---|---|
| ✅ | `gear_type` | bevel |
| ✅ | `is_internal_gear` | False |
| ✅ | `num_teeth` | 24 |
| ✅ | `module_mm` | 1.587  (erwartet: 1.587,  Δ=0.0%) |
| ✅ | `outer_diameter_mm` | 38.554  (erwartet: 39.116,  Δ=1.4%) |
| ✅ | `pitch_diameter_mm` | 38.100  (erwartet: 38.100,  Δ=0.0%) |
| ✅ | `face_width_mm` | 4.826  (erwartet: 4.826,  Δ=0.0%) |
| ✅ | `helix_angle_deg` | 0.000  (erwartet: 0) |
| ✅ | `pressure_angle_deg` | 20.000  (erwartet: 20.000,  Δ=0.0%) |
| ✅ | `bore_diameter_mm` | 12.700  (erwartet: 12.700,  Δ=0.0%) |
| ✅ | `overall_width_mm` | 19.012  (erwartet: 18.821,  Δ=1.0%) |
| ✅ | `hub_diameter_mm` | 25.400  (erwartet: 25.400,  Δ=0.0%) |

**Ergebnis: 12/12 OK  (0 ⚠  0 ✗  0 ?)**

#### `2515N15_Metal Bevel Gear.STEP`  
<sub>2515N15 · 1144 Carbon Steel</sub>

| Status | Parameter | Messung / Vergleich |
|:--:|---|---|
| ✅ | `gear_type` | bevel |
| ✅ | `is_internal_gear` | False |
| ✅ | `num_teeth` | 48 |
| ✅ | `module_mm` | 1.587  (erwartet: 1.587,  Δ=0.0%) |
| ✅ | `outer_diameter_mm` | 76.640  (erwartet: 76.708,  Δ=0.1%) |
| ✅ | `pitch_diameter_mm` | 76.200  (erwartet: 76.200,  Δ=0.0%) |
| ✅ | `face_width_mm` | 10.668  (erwartet: 10.668,  Δ=0.0%) |
| ✅ | `helix_angle_deg` | 0.000  (erwartet: 0) |
| ✅ | `pressure_angle_deg` | 20.000  (erwartet: 20.000,  Δ=0.0%) |
| ✅ | `bore_diameter_mm` | 15.875  (erwartet: 15.875,  Δ=0.0%) |
| ✅ | `overall_width_mm` | 24.899  (erwartet: 24.714,  Δ=0.7%) |
| ✅ | `hub_diameter_mm` | 38.100  (erwartet: 38.100,  Δ=0.0%) |

**Ergebnis: 12/12 OK  (0 ⚠  0 ✗  0 ?)**

#### `2515N336_Metal Bevel Gear.STEP`  
<sub>2515N336 · Black-Oxide 1045 Carbon Steel</sub>

| Status | Parameter | Messung / Vergleich |
|:--:|---|---|
| ✅ | `gear_type` | bevel |
| ✅ | `is_internal_gear` | False |
| ✅ | `num_teeth` | 40 |
| ✅ | `module_mm` | 1.000  (erwartet: 1.000,  Δ=0.0%) |
| ✅ | `outer_diameter_mm` | 40.828  (erwartet: 40.600,  Δ=0.6%) |
| ✅ | `pitch_diameter_mm` | 40.000  (erwartet: 40.000,  Δ=0.0%) |
| ✅ | `face_width_mm` | 5.980  (erwartet: 6.000,  Δ=0.3%) |
| ✅ | `helix_angle_deg` | 0.000  (erwartet: 0) |
| ✅ | `pressure_angle_deg` | 20.000  (erwartet: 20.000,  Δ=0.0%) |
| ⚠️ | `bore_diameter_mm` | 7.825  (erwartet: 8.000,  Δ=2.2%) |
| ⚠️ | `overall_width_mm` | 15.370  (erwartet: 15.000,  Δ=2.5%) |
| ✅ | `hub_diameter_mm` | 25.000  (erwartet: 25.000,  Δ=0.0%) |

**Ergebnis: 10/12 OK  (2 ⚠  0 ✗  0 ?)**

#### `2515N355_Metal Bevel Gear.STEP`  
<sub>2515N355 · Black-Oxide 1045 Carbon Steel</sub>

| Status | Parameter | Messung / Vergleich |
|:--:|---|---|
| ✅ | `gear_type` | bevel |
| ✅ | `is_internal_gear` | False |
| ✅ | `num_teeth` | 60 |
| ✅ | `module_mm` | 2.500  (erwartet: 2.500,  Δ=0.0%) |
| ✅ | `outer_diameter_mm` | 150.523  (erwartet: 150.500,  Δ=0.0%) |
| ✅ | `pitch_diameter_mm` | 150.000  (erwartet: 150.000,  Δ=0.0%) |
| ✅ | `face_width_mm` | 19.917  (erwartet: 20.000,  Δ=0.4%) |
| ✅ | `helix_angle_deg` | 0.000  (erwartet: 0) |
| ✅ | `pressure_angle_deg` | 20.000  (erwartet: 20.000,  Δ=0.0%) |
| ✅ | `bore_diameter_mm` | 20.000  (erwartet: 20.000,  Δ=0.0%) |
| ✅ | `overall_width_mm` | 40.632  (erwartet: 40.000,  Δ=1.6%) |
| ✅ | `hub_diameter_mm` | 70.000  (erwartet: 70.000,  Δ=0.0%) |

**Ergebnis: 12/12 OK  (0 ⚠  0 ✗  0 ?)**

#### `3856N121_Plastic Bevel Gear.STEP`  
<sub>3856N121 · Nylon</sub>

| Status | Parameter | Messung / Vergleich |
|:--:|---|---|
| ✅ | `gear_type` | bevel |
| ✅ | `is_internal_gear` | False |
| ✅ | `num_teeth` | 40 |
| ✅ | `module_mm` | 1.000  (erwartet: 1.000,  Δ=0.0%) |
| ✅ | `outer_diameter_mm` | 40.434  (erwartet: 40.600,  Δ=0.4%) |
| ✅ | `pitch_diameter_mm` | 40.000  (erwartet: 40.000,  Δ=0.0%) |
| ✅ | `face_width_mm` | 5.955  (erwartet: 6.000,  Δ=0.7%) |
| ✅ | `helix_angle_deg` | 0.000  (erwartet: 0) |
| ✅ | `pressure_angle_deg` | 20.000  (erwartet: 20.000,  Δ=0.0%) |
| ✅ | `bore_diameter_mm` | 8.000  (erwartet: 8.000,  Δ=0.0%) |
| ✅ | `overall_width_mm` | 15.262  (erwartet: 15.000,  Δ=1.7%) |
| ✅ | `hub_diameter_mm` | 25.000  (erwartet: 25.000,  Δ=0.0%) |

**Ergebnis: 12/12 OK  (0 ⚠  0 ✗  0 ?)**

#### `6010N13_High-Power Metal Bevel Gear.STEP`  
<sub>6010N13 · Black-Oxide 1045 Carbon Steel</sub>

| Status | Parameter | Messung / Vergleich |
|:--:|---|---|
| ✅ | `gear_type` | bevel |
| ✅ | `is_internal_gear` | False |
| ✅ | `num_teeth` | 40 |
| ✅ | `module_mm` | 1.500  (erwartet: 1.500,  Δ=0.0%) |
| ✅ | `outer_diameter_mm` | 60.318  (erwartet: 60.750,  Δ=0.7%) |
| ✅ | `pitch_diameter_mm` | 60.000  (erwartet: 60.000,  Δ=0.0%) |
| ✅ | `face_width_mm` | 9.891  (erwartet: 10.000,  Δ=1.1%) |
| ✅ | `pressure_angle_deg` | 20.000  (erwartet: 20.000,  Δ=0.0%) |
| ✅ | `overall_width_mm` | 25.353  (erwartet: 24.900,  Δ=1.8%) |
| ✅ | `hub_diameter_mm` | 38.000  (erwartet: 38.000,  Δ=0.0%) |

**Ergebnis: 10/10 OK  (0 ⚠  0 ✗  0 ?)**

### Gehrungsräder (miter)

#### `2600N14_Metal Miter Gear.STEP`  
<sub>1045 Carbon Steel</sub>

| Status | Parameter | Messung / Vergleich |
|:--:|---|---|
| ✅ | `gear_type` | miter |
| ✅ | `is_internal_gear` | False |
| ✅ | `num_teeth` | 25 |
| ✅ | `module_mm` | 2.000  (erwartet: 2.000,  Δ=0.0%) |
| ✅ | `outer_diameter_mm` | 52.387  (erwartet: 52.800,  Δ=0.8%) |
| ✅ | `pitch_diameter_mm` | 50.000  (erwartet: 50.000,  Δ=0.0%) |
| ✅ | `overall_width_mm` | 24.354  (erwartet: 24.300,  Δ=0.2%) |
| ✅ | `bore_diameter_mm` | 14.804  (erwartet: 15.000,  Δ=1.3%) |
| ❔ | `hub_diameter_mm` | None  (erwartet: 40.0) |
| ❔ | `hub_width_mm` | None  (erwartet: 10.0) |
| ✅ | `shaft_angle_deg` | 90.000  (erwartet: 90.000,  Δ=0.0%) |
| ✅ | `cone_angle_deg` | 45.000  (erwartet: 45.000,  Δ=0.0%) |
| ✅ | `helix_angle_deg` | 0.000  (erwartet: 0) |
| ✅ | `pressure_angle_deg` | 20.000  (erwartet: 20.000,  Δ=0.0%) |

**Ergebnis: 12/14 OK  (0 ⚠  0 ✗  2 ?)**

#### `2600N15_Metal Miter Gear.STEP`  
<sub>1045 Carbon Steel</sub>

| Status | Parameter | Messung / Vergleich |
|:--:|---|---|
| ✅ | `gear_type` | miter |
| ✅ | `is_internal_gear` | False |
| ✅ | `num_teeth` | 30 |
| ✅ | `module_mm` | 2.000  (erwartet: 2.000,  Δ=0.0%) |
| ✅ | `outer_diameter_mm` | 62.347  (erwartet: 62.800,  Δ=0.7%) |
| ✅ | `pitch_diameter_mm` | 60.000  (erwartet: 60.000,  Δ=0.0%) |
| ✅ | `overall_width_mm` | 29.364  (erwartet: 29.400,  Δ=0.1%) |
| ✅ | `bore_diameter_mm` | 14.852  (erwartet: 15.000,  Δ=1.0%) |
| ❔ | `hub_diameter_mm` | None  (erwartet: 45.0) |
| ❔ | `hub_width_mm` | None  (erwartet: 12.5) |
| ✅ | `shaft_angle_deg` | 90.000  (erwartet: 90.000,  Δ=0.0%) |
| ✅ | `cone_angle_deg` | 45.000  (erwartet: 45.000,  Δ=0.0%) |
| ✅ | `helix_angle_deg` | 0.000  (erwartet: 0) |
| ✅ | `pressure_angle_deg` | 20.000  (erwartet: 20.000,  Δ=0.0%) |

**Ergebnis: 12/14 OK  (0 ⚠  0 ✗  2 ?)**

#### `2600N5_Metal Miter Gear.STEP`  
<sub>1045 Carbon Steel</sub>

| Status | Parameter | Messung / Vergleich |
|:--:|---|---|
| ✅ | `gear_type` | miter |
| ✅ | `is_internal_gear` | False |
| ✅ | `num_teeth` | 20 |
| ✅ | `module_mm` | 2.000  (erwartet: 2.000,  Δ=0.0%) |
| ✅ | `outer_diameter_mm` | 42.505  (erwartet: 42.800,  Δ=0.7%) |
| ✅ | `pitch_diameter_mm` | 40.000  (erwartet: 40.000,  Δ=0.0%) |
| ✅ | `overall_width_mm` | 24.900  (erwartet: 24.900,  Δ=0.0%) |
| ✅ | `bore_diameter_mm` | 14.706  (erwartet: 15.000,  Δ=2.0%) |
| ✅ | `hub_diameter_mm` | 34.000  (erwartet: 34.000,  Δ=0.0%) |
| ✅ | `hub_width_mm` | 13.763  (erwartet: 14.000,  Δ=1.7%) |
| ✅ | `shaft_angle_deg` | 90.000  (erwartet: 90.000,  Δ=0.0%) |
| ✅ | `cone_angle_deg` | 45.000  (erwartet: 45.000,  Δ=0.0%) |
| ✅ | `helix_angle_deg` | 0.000  (erwartet: 0) |
| ✅ | `pressure_angle_deg` | 20.000  (erwartet: 20.000,  Δ=0.0%) |

**Ergebnis: 14/14 OK  (0 ⚠  0 ✗  0 ?)**

#### `2810N2_Plastic Miter Gear.STEP`  
<sub>Acetal</sub>

| Status | Parameter | Messung / Vergleich |
|:--:|---|---|
| ✅ | `gear_type` | miter |
| ✅ | `is_internal_gear` | False |
| ✅ | `num_teeth` | 20 |
| ✅ | `module_mm` | 0.794  (erwartet: 0.800,  Δ=0.8%) |
| ✅ | `outer_diameter_mm` | 16.917  (erwartet: 17.100,  Δ=1.1%) |
| ✅ | `pitch_diameter_mm` | 15.874  (erwartet: 16.000,  Δ=0.8%) |
| ✅ | `overall_width_mm` | 10.800  (erwartet: 10.800,  Δ=0.0%) |
| ✅ | `bore_diameter_mm` | 5.000  (erwartet: 5.000,  Δ=0.0%) |
| ✅ | `shaft_angle_deg` | 90.000  (erwartet: 90.000,  Δ=0.0%) |
| ✅ | `cone_angle_deg` | 45.000  (erwartet: 45.000,  Δ=0.0%) |
| ✅ | `helix_angle_deg` | 0.000  (erwartet: 0) |
| ✅ | `pressure_angle_deg` | 20.000  (erwartet: 20.000,  Δ=0.0%) |

**Ergebnis: 12/12 OK  (0 ⚠  0 ✗  0 ?)**

#### `3560N14_Metal Miter Gear.STEP`  
<sub>303 Stainless Steel</sub>

| Status | Parameter | Messung / Vergleich |
|:--:|---|---|
| ✅ | `gear_type` | miter |
| ✅ | `is_internal_gear` | False |
| ✅ | `num_teeth` | 25 |
| ✅ | `module_mm` | 1.000  (erwartet: 1.000,  Δ=0.0%) |
| ✅ | `outer_diameter_mm` | 26.313  (erwartet: 26.400,  Δ=0.3%) |
| ✅ | `pitch_diameter_mm` | 25.000  (erwartet: 25.000,  Δ=0.0%) |
| ✅ | `overall_width_mm` | 15.234  (erwartet: 15.200,  Δ=0.2%) |
| ✅ | `bore_diameter_mm` | 5.886  (erwartet: 6.000,  Δ=1.9%) |
| ✅ | `hub_diameter_mm` | 20.000  (erwartet: 20.000,  Δ=0.0%) |
| ✅ | `hub_width_mm` | 7.849  (erwartet: 8.000,  Δ=1.9%) |
| ✅ | `shaft_angle_deg` | 90.000  (erwartet: 90.000,  Δ=0.0%) |
| ✅ | `cone_angle_deg` | 45.000  (erwartet: 45.000,  Δ=0.0%) |
| ✅ | `helix_angle_deg` | 0.000  (erwartet: 0) |
| ✅ | `pressure_angle_deg` | 20.000  (erwartet: 20.000,  Δ=0.0%) |

**Ergebnis: 14/14 OK  (0 ⚠  0 ✗  0 ?)**

#### `6529K57_Metal Miter Gear.STEP`

| Status | Parameter | Messung / Vergleich |
|:--:|---|---|
| ✅ | `gear_type` | miter |
| ✅ | `is_internal_gear` | False |
| ✅ | `num_teeth` | 20 |
| ✅ | `module_mm` | 1.500  (erwartet: 1.500,  Δ=0.0%) |
| ✅ | `pitch_diameter_mm` | 30.000  (erwartet: 30.000,  Δ=0.0%) |
| ✅ | `bore_diameter_mm` | 8.000  (erwartet: 8.000,  Δ=0.0%) |
| ✅ | `hub_diameter_mm` | 25.000  (erwartet: 25.000,  Δ=0.0%) |
| ✅ | `helix_angle_deg` | 0.000  (erwartet: 0) |
| ✅ | `pressure_angle_deg` | 20.000  (erwartet: 20.000,  Δ=0.0%) |

**Ergebnis: 9/9 OK  (0 ⚠  0 ✗  0 ?)**

#### `6529K58_Metal Miter Gear.STEP`  
<sub>1045 Carbon Steel</sub>

| Status | Parameter | Messung / Vergleich |
|:--:|---|---|
| ✅ | `gear_type` | miter |
| ✅ | `is_internal_gear` | False |
| ✅ | `num_teeth` | 20 |
| ✅ | `module_mm` | 1.500  (erwartet: 1.500,  Δ=0.0%) |
| ✅ | `outer_diameter_mm` | 32.464  (erwartet: 32.600,  Δ=0.4%) |
| ✅ | `pitch_diameter_mm` | 30.000  (erwartet: 30.000,  Δ=0.0%) |
| ✅ | `overall_width_mm` | 22.300  (erwartet: 22.300,  Δ=0.0%) |
| ✅ | `bore_diameter_mm` | 8.000  (erwartet: 8.000,  Δ=0.0%) |
| ✅ | `hub_diameter_mm` | 25.000  (erwartet: 25.000,  Δ=0.0%) |
| ✅ | `hub_width_mm` | 12.600  (erwartet: 12.600,  Δ=0.0%) |
| ✅ | `shaft_angle_deg` | 60.000  (erwartet: 60.000,  Δ=0.0%) |
| ✅ | `cone_angle_deg` | 30.000  (erwartet: 30.000,  Δ=0.0%) |
| ✅ | `helix_angle_deg` | 0.000  (erwartet: 0) |
| ✅ | `pressure_angle_deg` | 20.000  (erwartet: 20.000,  Δ=0.0%) |

**Ergebnis: 14/14 OK  (0 ⚠  0 ✗  0 ?)**

#### `6529K61_Metal Miter Gear.STEP`  
<sub>1045 Carbon Steel</sub>

| Status | Parameter | Messung / Vergleich |
|:--:|---|---|
| ✅ | `gear_type` | miter |
| ✅ | `is_internal_gear` | False |
| ✅ | `num_teeth` | 20 |
| ✅ | `module_mm` | 2.500  (erwartet: 2.500,  Δ=0.0%) |
| ✅ | `outer_diameter_mm` | 53.597  (erwartet: 54.600,  Δ=1.8%) |
| ✅ | `pitch_diameter_mm` | 50.000  (erwartet: 50.000,  Δ=0.0%) |
| ✅ | `overall_width_mm` | 31.920  (erwartet: 31.900,  Δ=0.1%) |
| ✅ | `bore_diameter_mm` | 12.000  (erwartet: 12.000,  Δ=0.0%) |
| ✅ | `hub_diameter_mm` | 40.000  (erwartet: 40.000,  Δ=0.0%) |
| ✅ | `hub_width_mm` | 12.600  (erwartet: 12.600,  Δ=0.0%) |
| ✅ | `shaft_angle_deg` | 45.000  (erwartet: 45.000,  Δ=0.0%) |
| ✅ | `cone_angle_deg` | 22.500  (erwartet: 22.500,  Δ=0.0%) |
| ✅ | `helix_angle_deg` | 0.000  (erwartet: 0) |
| ✅ | `pressure_angle_deg` | 20.000  (erwartet: 20.000,  Δ=0.0%) |

**Ergebnis: 14/14 OK  (0 ⚠  0 ✗  0 ?)**

### Ratschenräder (ratchet)

#### `2540N13_Plastic Ratcheting Gear.STEP`  
<sub>2540N13 · Nylon</sub>

| Status | Parameter | Messung / Vergleich |
|:--:|---|---|
| ✅ | `gear_type` | ratchet |
| ✅ | `is_internal_gear` | False |
| ✅ | `num_teeth` | 24 |
| ✅ | `outer_diameter_mm` | 25.400  (erwartet: 25.400,  Δ=0.0%) |
| ✅ | `face_width_mm` | 6.350  (erwartet: 6.350,  Δ=0.0%) |
| ✅ | `bore_diameter_mm` | 9.525  (erwartet: 9.525,  Δ=0.0%) |
| ✅ | `overall_width_mm` | 6.350  (erwartet: 6.350,  Δ=0.0%) |

**Ergebnis: 7/7 OK  (0 ⚠  0 ✗  0 ?)**

#### `6283K121_Metal Ratcheting Gear.STEP`  
<sub>6283K121 · 1045 Carbon Steel</sub>

| Status | Parameter | Messung / Vergleich |
|:--:|---|---|
| ✅ | `gear_type` | ratchet |
| ✅ | `is_internal_gear` | False |
| ✅ | `num_teeth` | 50 |
| ✅ | `outer_diameter_mm` | 200.000  (erwartet: 200.000,  Δ=0.0%) |
| ✅ | `face_width_mm` | 25.000  (erwartet: 25.000,  Δ=0.0%) |
| ✅ | `bore_diameter_mm` | 20.000  (erwartet: 20.000,  Δ=0.0%) |
| ✅ | `overall_width_mm` | 43.000  (erwartet: 43.000,  Δ=0.0%) |
| ✅ | `hub_diameter_mm` | 100.000  (erwartet: 100.000,  Δ=0.0%) |

**Ergebnis: 8/8 OK  (0 ⚠  0 ✗  0 ?)**

#### `6283K12_Metal Ratcheting Gear.STEP`  
<sub>6283K12 · 303 Stainless Steel</sub>

| Status | Parameter | Messung / Vergleich |
|:--:|---|---|
| ✅ | `gear_type` | ratchet |
| ✅ | `is_internal_gear` | False |
| ✅ | `num_teeth` | 18 |
| ✅ | `outer_diameter_mm` | 19.050  (erwartet: 19.050,  Δ=0.0%) |
| ✅ | `face_width_mm` | 6.350  (erwartet: 6.350,  Δ=0.0%) |
| ✅ | `bore_diameter_mm` | 9.525  (erwartet: 9.525,  Δ=0.0%) |
| ✅ | `overall_width_mm` | 6.350  (erwartet: 6.350,  Δ=0.0%) |

**Ergebnis: 7/7 OK  (0 ⚠  0 ✗  0 ?)**

#### `6283K24_Metal Ratcheting Gear.STEP`  
<sub>6283K24 · 303 Stainless Steel</sub>

| Status | Parameter | Messung / Vergleich |
|:--:|---|---|
| ✅ | `gear_type` | ratchet |
| ✅ | `is_internal_gear` | False |
| ✅ | `num_teeth` | 24 |
| ✅ | `outer_diameter_mm` | 38.100  (erwartet: 38.100,  Δ=0.0%) |
| ✅ | `face_width_mm` | 9.525  (erwartet: 9.525,  Δ=0.0%) |
| ✅ | `bore_diameter_mm` | 17.462  (erwartet: 17.462,  Δ=0.0%) |
| ✅ | `overall_width_mm` | 9.525  (erwartet: 9.525,  Δ=0.0%) |

**Ergebnis: 7/7 OK  (0 ⚠  0 ✗  0 ?)**

#### `6283K62_Metal Ratcheting Gear.STEP`

| Status | Parameter | Messung / Vergleich |
|:--:|---|---|
| ✅ | `gear_type` | ratchet |
| ✅ | `is_internal_gear` | False |
| ✅ | `num_teeth` | 50 |

**Ergebnis: 3/3 OK  (0 ⚠  0 ✗  0 ?)**

#### `6283K93_Metal Ratcheting Gear.STEP`  
<sub>6283K93 · 1045 Carbon Steel</sub>

| Status | Parameter | Messung / Vergleich |
|:--:|---|---|
| ✅ | `gear_type` | ratchet |
| ✅ | `is_internal_gear` | False |
| ✅ | `num_teeth` | 100 |
| ✅ | `outer_diameter_mm` | 100.000  (erwartet: 100.000,  Δ=0.0%) |
| ✅ | `face_width_mm` | 12.000  (erwartet: 12.000,  Δ=0.0%) |
| ✅ | `bore_diameter_mm` | 15.000  (erwartet: 15.000,  Δ=0.0%) |
| ✅ | `overall_width_mm` | 24.000  (erwartet: 24.000,  Δ=0.0%) |
| ✅ | `hub_diameter_mm` | 50.000  (erwartet: 50.000,  Δ=0.0%) |

**Ergebnis: 8/8 OK  (0 ⚠  0 ✗  0 ?)**

#### `6283K94_Metal Ratcheting Gear.STEP`  
<sub>6283K94 · 1045 Carbon Steel</sub>

| Status | Parameter | Messung / Vergleich |
|:--:|---|---|
| ✅ | `gear_type` | ratchet |
| ✅ | `is_internal_gear` | False |
| ✅ | `num_teeth` | 50 |
| ✅ | `outer_diameter_mm` | 50.000  (erwartet: 50.000,  Δ=0.0%) |
| ✅ | `face_width_mm` | 12.000  (erwartet: 12.000,  Δ=0.0%) |
| ✅ | `bore_diameter_mm` | 12.000  (erwartet: 12.000,  Δ=0.0%) |
| ✅ | `overall_width_mm` | 24.000  (erwartet: 24.000,  Δ=0.0%) |
| ✅ | `hub_diameter_mm` | 35.000  (erwartet: 35.000,  Δ=0.0%) |

**Ergebnis: 8/8 OK  (0 ⚠  0 ✗  0 ?)**

#### `6283K96_Metal Ratcheting Gear.STEP`  
<sub>6283K96 · 1045 Carbon Steel</sub>

| Status | Parameter | Messung / Vergleich |
|:--:|---|---|
| ✅ | `gear_type` | ratchet |
| ✅ | `is_internal_gear` | False |
| ✅ | `num_teeth` | 80 |
| ✅ | `outer_diameter_mm` | 80.000  (erwartet: 80.000,  Δ=0.0%) |
| ✅ | `face_width_mm` | 12.000  (erwartet: 12.000,  Δ=0.0%) |
| ✅ | `bore_diameter_mm` | 15.000  (erwartet: 15.000,  Δ=0.0%) |
| ✅ | `overall_width_mm` | 24.000  (erwartet: 24.000,  Δ=0.0%) |
| ✅ | `hub_diameter_mm` | 50.000  (erwartet: 50.000,  Δ=0.0%) |

**Ergebnis: 8/8 OK  (0 ⚠  0 ✗  0 ?)**

### Zahnstangen (rack)

#### `2485N205_Metal Gear Rack - 20 Degree Pressure Angle.STEP`  
<sub>2485N205 · 1045 Carbon Steel</sub>

| Status | Parameter | Messung / Vergleich |
|:--:|---|---|
| ❌ | `gear_type` | 'internal' != 'rack' |
| ❌ | `is_internal_gear` | True != False |
| ❌ | `module_mm` | 5.000  (erwartet: 2.000,  Δ=150.0%) |
| ✅ | `face_width_mm` | 20.000  (erwartet: 20.000,  Δ=0.0%) |
| ✅ | `pressure_angle_deg` | 20.000  (erwartet: 20.000,  Δ=0.0%) |

**Ergebnis: 2/5 OK  (0 ⚠  3 ✗  0 ?)**

## Legende & Hinweise

✅ OK (≤ 2 %) · ⚠️ Warnung (≤ 5 %) · ❌ Fehler (> 5 %) · ❔ nicht erkannt

- **Ratschenräder:** Modul, Teilkreis, Eingriffs-/Schrägungswinkel sind beim Sägezahn-Sperrrad bedeutungslos und werden nicht geprüft. Die Naben-Breite wird bei Bund-Naben nicht als Soll geführt (verrundeter Bund-Fuß).
- **Verbleibende Fehler** (vorbestehend, außerhalb des Verzahnungs-Scopes): die Zahnstange (linear → eigener Messpfad) sowie die Naben-Erkennung an zwei Gehrungsrädern (2600N14/15).
