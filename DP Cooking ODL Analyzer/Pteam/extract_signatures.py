import pandas as pd
import numpy as np

def extract_batch_signatures(input_file, output_file):
    print(f"Reading cleaned data from {input_file}...")
    df = pd.read_excel(input_file)
    
    status_cols = [
        'Dig1_Discharge_BatchStatus', 
        'Dig2_Discharge_BatchStatus', 
        'Dig3_Discharge_BatchStatus', 
        'Dig4_Discharge_BatchStatus'
    ]
    
    press_cols = [
        'Dig1_Press1_BatchStatus', 
        'Dig2_Press1_BatchStatus', 
        'Dig3_Press1_BatchStatus', 
        'Dig4_Press1_BatchStatus'
    ]
    
    # Identify which columns are operational parameters (exclude Time and Status cols)
    exclude_cols = ['Time'] + status_cols + press_cols
    param_cols = [col for col in df.columns if col not in exclude_cols]
    
    # CONVERT PARAMETERS TO NUMERIC (Handle 'Out of Serv', 'I/O Timeout', etc.)
    print("Converting parameters to numeric and handling sensor errors...")
    for col in param_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    # CALCULATE SPECIFIC CONSUMPTION METRICS (t/ADT, m3/ADT, kg/ADT)
    # ADT = Air-Dried Ton, calculated as Production ODL (ADT/D) * 24 hours 
    prod_col = 'Production ODL (ADT/D)'
    steam_col = 'MP Steam Pulp Heat_Feed before Reactor 2 (t/h)'
    wl_col = 'WHLiqu to DilSrew_White liquor (m3/h)'
    o2_mixer_col = 'O2 to Mixer1_Oxygen feed at Reactor 1 (kg/h)'
    o2_pulp_col = 'O2 to pulp heater_Oxygen feed at Reactor 2 (kg/h)'
    
    # 24 * Feed / Production
    new_steam = 'Specific Steam Consumption (t_ADT)'
    new_wl = 'Specific WHLiqu Consumption (m3_ADT)'
    new_o2_mixer = 'Specific O2 Mixer 1 Consumption (kg_ADT)'
    new_o2_pulp = 'Specific O2 Pulp Heater Consumption (kg_ADT)'
    
    if prod_col in df.columns:
        print("Calculating Specific Consumption parameters...")
        # Replace 0 or negative values in Production with NaN to avoid division by zero
        temp_prod = df[prod_col].copy() #ADT/D
        temp_prod[temp_prod <= 0] = np.nan

        # invert to per hour
        # 1. Specific Steam
        if steam_col in df.columns:
            df[new_steam] = 24.0 * df[steam_col] / temp_prod
            param_cols.append(new_steam)
            
        # 2. Specific White Liquor
        if wl_col in df.columns:
            df[new_wl] = 24.0 * df[wl_col] / temp_prod
            param_cols.append(new_wl)
            
        # 3. Specific O2 Mixer 1
        if o2_mixer_col in df.columns:
            df[new_o2_mixer] = 24.0 * df[o2_mixer_col] / temp_prod
            param_cols.append(new_o2_mixer)
            
        # 4. Specific O2 Pulp Heater
        if o2_pulp_col in df.columns:
            df[new_o2_pulp] = 24.0 * df[o2_pulp_col] / temp_prod
            param_cols.append(new_o2_pulp)
    else:
        print(f"Warning: Production column '{prod_col}' not found.")
        
    # Convert status and press columns to numeric, filling NaNs/strings with 0
    for col in status_cols + press_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Create a single 'Active_Digester' column to simplify grouping of original discharge batches
    df['Active_Digester'] = df[status_cols].max(axis=1).astype(int)
    
    # Identify continuous blocks of the same digester discharge activity
    df['block_id'] = (df['Active_Digester'] != df['Active_Digester'].shift(1)).cumsum()
    
    # We find raw discharge blocks where active digester > 0
    batch_df = df[df['Active_Digester'] > 0].copy()
    
    print("Identifying discharge-based batch windows...")
    grouped = batch_df.groupby(['block_id', 'Active_Digester'])
    original_batches = []
    for (block, dig_id), gp in grouped:
        original_batches.append({
            'Digester_ID': dig_id,
            'Start_Idx': gp.index[0],
            'End_Idx': gp.index[-1]
        })
        
    print(f"Found {len(original_batches)} raw discharge-based batches.")
    print("Scanning forward to extend batches through sequential Press 1 activity...")
    
    extended_batches = []
    for idx, batch in enumerate(original_batches):
        dig_id = batch['Digester_ID']
        p_col = f'Dig{dig_id}_Press1_BatchStatus'
        
        start_idx = batch['Start_Idx']
        end_idx = batch['End_Idx']
        
        # Determine scanning boundaries to prevent overlapping with the next discharge of the SAME digester
        next_same_dig_start = len(df)
        for next_batch in original_batches[idx+1:]:
            if next_batch['Digester_ID'] == dig_id:
                next_same_dig_start = next_batch['Start_Idx']
                break
                
        # Scan forward from the discharge start
        curr_idx = start_idx
        extended_end_idx = end_idx
        
        # Limit scanning to avoid overlapping next batch, and cap at +60 rows (5 hours) to prevent runaway
        max_idx = min(next_same_dig_start, len(df))
        max_idx = min(max_idx, start_idx + 60)
        
        while curr_idx < max_idx:
            if df.loc[curr_idx, p_col] > 0:
                extended_end_idx = max(extended_end_idx, curr_idx)
            curr_idx += 1
            
        extended_batches.append({
            'Digester_ID': dig_id,
            'Start_Idx': start_idx,
            'End_Idx': extended_end_idx
        })
        
    print("Aggregating batch statistics over extended windows...")
    batch_signatures = []
    for batch in extended_batches:
        dig_id = batch['Digester_ID']
        start_idx = batch['Start_Idx']
        end_idx = batch['End_Idx']
        
        batch_slice = df.loc[start_idx:end_idx]
        
        stats = {
            'Digester_ID': dig_id,
            'Start_Time': batch_slice['Time'].iloc[0],
            'End_Time': batch_slice['Time'].iloc[-1],
            'Row_Count': len(batch_slice),
            'Duration_Min': len(batch_slice) * 5
        }
        
        # Calculate Mean and Std for all parameters
        for col in param_cols:
            stats[f"{col}_mean"] = batch_slice[col].mean()
            stats[f"{col}_std"] = batch_slice[col].std()
            
        batch_signatures.append(stats)
        
    final_batches = pd.DataFrame(batch_signatures)
    
    print(f"Extracted {len(final_batches)} batches.")
    print(f"Saving to {output_file}...")
    final_batches.to_excel(output_file, index=False)
    print("Done.")

if __name__ == "__main__":
    extract_batch_signatures('df_filtered_PPPC_DPCooking.xlsx', 'df_batch_signatures.xlsx')
