import pandas as pd
import numpy as np

def clean_digester_status(input_file, output_file):
    print(f"Reading {input_file}...")
    df = pd.read_excel(input_file)
    
    status_cols = [
        'Dig1_Discharge_BatchStatus', 
        'Dig2_Discharge_BatchStatus', 
        'Dig3_Discharge_BatchStatus', 
        'Dig4_Discharge_BatchStatus'
    ]
    
    # Ensure status columns are numeric to handle 'No Data' etc.
    for col in status_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Store the cleaned values
    cleaned_data = []
    last_active = 0
    
    print("Processing rows...")
    for index, row in df.iterrows():
        # Identify candidates: those with value > 0
        candidates = []
        for i, col in enumerate(status_cols, 1):
            if row[col] > 0:
                candidates.append(i)
        
        winner = 0
        if last_active in candidates:
            # If the previously active digester is still "showing" activity, stick with it
            winner = last_active
        elif len(candidates) > 0:
            # If the previous one stopped, pick the new one. 
            # If multiple start at once, pick the one with the highest normalized value
            # (value / expected_id)
            winner = max(candidates, key=lambda x: row[status_cols[x-1]] / x)
        else:
            winner = 0
            
        # Update last_active
        last_active = winner
        
        # Create the cleaned row for status columns
        cleaned_row = {}
        for i, col in enumerate(status_cols, 1):
            cleaned_row[col] = float(i) if i == winner else 0.0
        cleaned_data.append(cleaned_row)
    
    # Apply cleaned data back to dataframe
    cleaned_df = pd.DataFrame(cleaned_data)
    for col in status_cols:
        df[col] = cleaned_df[col]
        
    print(f"Saving to {output_file}...")
    df.to_excel(output_file, index=False)
    print("Done.")

if __name__ == "__main__":
    clean_digester_status('df_imported_PPPC_DPCooking.xlsx', 'df_filtered_PPPC_DPCooking.xlsx')
