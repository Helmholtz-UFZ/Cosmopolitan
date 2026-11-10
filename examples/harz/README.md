# Example data: Harz

CRNS rover measurements from one day (2025-06-30) in the Harz region, Germany,
for a COSMOPOLITAN soil moisture prediction.

| File | Content |
|---|---|
| `crns_rover_harz_20250630.csv` | 1230 points: x, y (EPSG:25832), date, soil moisture, lower error, upper error; no header row |

## Use

1. Start the app (see Quick Start in the top-level README) and create a job.
2. Set the area to the Harz grid:

   | Field | Value |
   |---|---|
   | X1 | 619500 |
   | X2 | 680750 |
   | Y1 | 5713500 |
   | Y2 | 5786500 |
   | Resolution | 250 |
   | Projection | EPSG:25832 |

3. Upload `crns_rover_harz_20250630.csv` as CRNS data and untick train, station
   and rover data: a job takes either uploaded CRNS data or the database
   sources, not both.
4. Keep the default predictor streams; no predictor file is needed.
5. Submit the job.
