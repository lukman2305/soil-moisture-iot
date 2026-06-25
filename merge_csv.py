import csv
import glob
from datetime import datetime
import os

files = [f for f in glob.glob('*data*.csv') if 'merged' not in f and not f.startswith('test')]
print("Found files:", files)

# We want to identify the header. All files should have the same columns,
# but we'll take the longest one just in case.
header = []
data_rows = {}

for f in files:
    try:
        with open(f, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            rows = list(reader)
            if not rows: continue
            
            curr_header = rows[0]
            if len(curr_header) > len(header):
                header = curr_header
                
            for row in rows[1:]:
                if not row or not row[0].strip(): continue
                # Parse timestamp to sort
                ts_str = row[0]
                try:
                    # '2026-06-12 19:27:38.405638' or '2026-06-20 02:02:14'
                    if '.' in ts_str:
                        ts = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S.%f')
                    else:
                        ts = datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
                    
                    # Store by timestamp to automatically remove duplicates
                    # Pad the row to match the longest header if needed
                    padded_row = row + [''] * (len(header) - len(row))
                    data_rows[ts] = padded_row
                except Exception as parse_e:
                    pass
    except Exception as e:
        print(f"Error reading {f}: {e}")

if data_rows:
    sorted_times = sorted(data_rows.keys())
    
    with open('merged_plant_data.csv', 'w', newline='', encoding='utf-8') as out:
        writer = csv.writer(out)
        writer.writerow(header)
        for ts in sorted_times:
            writer.writerow(data_rows[ts])
            
    print(f"\nSuccessfully created merged_plant_data.csv with {len(sorted_times)} total rows!")
    print(f"Data ranges from {sorted_times[0]} to {sorted_times[-1]}")
else:
    print("No valid data found.")
