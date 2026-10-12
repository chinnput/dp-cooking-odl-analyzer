import pandas as pd
import numpy as np

def generate_sop_reference(input_file, output_file):
    print(f"Reading clustered data from {input_file}...")
    df = pd.read_excel(input_file)
    
    # Filter for Normal batches only (This defines our SOP)
    normal_df = df[df['Status_Flag'] == 'Normal'].copy()
    
    # Identify all mean parameters
    mean_params = [col for col in df.columns if col.endswith('_mean')]
    
    sop_data = []
    
    print(f"Calculating SOP windows for {len(mean_params)} parameters...")
    
    for param in mean_params:
        # Convert to numeric just in case and drop NaNs
        data = pd.to_numeric(normal_df[param], errors='coerce').dropna()
        
        if len(data) > 0:
            lower_limit = data.quantile(0.05)
            upper_limit = data.quantile(0.95)
            mean_val = data.mean()
            std_val = data.std()
            
            sop_data.append({
                'Parameter': param.replace('_mean', ''),
                'SOP_Lower_Limit (5th%)': lower_limit,
                'SOP_Target (Mean)': mean_val,
                'SOP_Upper_Limit (95th%)': upper_limit,
                'SOP_Std_Dev (Stability)': std_val
            })
        else:
            print(f"Skipping {param}: No data found in Normal cluster.")
            
    # Create the reference dataframe
    sop_ref_df = pd.DataFrame(sop_data)
    
    # Sort by parameter name for easy reading
    sop_ref_df = sop_ref_df.sort_values(by='Parameter')
    
    print(f"Saving SOP Reference Table to {output_file}...")
    sop_ref_df.to_excel(output_file, index=False)
    
    # Also print the top 10 for immediate feedback
    print("\nSample SOP Reference (Top 10):")
    print(sop_ref_df.head(10).to_string(index=False))
    
    print("\nDone.")

if __name__ == "__main__":
    generate_sop_reference('df_clustered_batches.xlsx', 'sop_limits_reference.xlsx')
