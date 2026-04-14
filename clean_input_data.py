#!/usr/bin/env python3
"""Quick script to remove quotes and whitespace from CSV."""

import pandas as pd
import re

# Read raw file and manually strip quotes
with open('Daten/V2/Prod/InputData.csv', 'r', encoding='utf-8-sig') as f:
    lines = f.readlines()

# Remove quotes from each line, then parse
cleaned_lines = []
for line in lines:
    # Remove leading/trailing quotes and whitespace
    line = line.strip()
    if line.startswith('"') and line.endswith('"'):
        line = line[1:-1]  # Remove outer quotes
    cleaned_lines.append(line)

# Write temp cleaned file
temp_file = 'Daten/V2/Prod/InputData_temp.csv'
with open(temp_file, 'w', encoding='utf-8-sig') as f:
    f.write('\n'.join(cleaned_lines))

# Now read with pandas
df = pd.read_csv(temp_file, sep=';', encoding='utf-8-sig')

# Strip whitespace from all string columns
df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)

# Save cleaned file
output_path = 'Daten/V2/Prod/InputData_cleaned.csv'
df.to_csv(output_path, sep=';', index=False, encoding='utf-8-sig')

# Cleanup temp
import os
os.remove(temp_file)

print(f"✅ Cleaned! Saved to: {output_path}")
print(f"   Rows: {len(df)}")
print(f"\nFirst 3 rows:")
print(df.head(3))
