import pandas as pd
import numpy as np

def analyze_digester_performance(input_file, output_file):
    print(f"Reading clustered data from {input_file}...")
    df = pd.read_excel(input_file)
    
    # 1. Basic Counts and Abnormality Rates
    performance = df.groupby('Digester_ID').agg({
        'Status_Flag': lambda x: (x == 'Abnormal').sum(),
        'Cluster_Distance': ['count', 'mean', 'std', 'max']
    })
    
    # Flatten columns
    performance.columns = ['Abnormal_Count', 'Total_Batches', 'Avg_Deviation_Score', 'Deviation_Stability', 'Max_Deviation']
    
    # Calculate Abnormality Rate (%)
    performance['Abnormality_Rate_Pct'] = (performance['Abnormal_Count'] / performance['Total_Batches']) * 100
    
    # 2. Reliability Ranking (Lower Abnormality Rate + Lower Avg Deviation = More Reliable)
    # A "Perfect" score would be 0 abnormality and 0 deviation.
    performance = performance.sort_values(by='Abnormality_Rate_Pct')
    
    # 3. Identify specific parameters where each digester varies most
    # We compare each digester's mean vs the global SOP target
    mean_params = [col for col in df.columns if col.endswith('_mean')]
    sop_targets = df[df['Status_Flag'] == 'Normal'][mean_params].mean()
    
    digester_means = df.groupby('Digester_ID')[mean_params].mean()
    
    # Calculate % drift from SOP for each digester
    drift = ((digester_means - sop_targets) / sop_targets) * 100
    
    print("\nDigester Reliability Summary:")
    print(performance[['Total_Batches', 'Abnormal_Count', 'Abnormality_Rate_Pct', 'Avg_Deviation_Score']].to_string())
    
    # Save results
    with pd.ExcelWriter(output_file) as writer:
        performance.to_excel(writer, sheet_name='Reliability_Ranking')
        drift.to_excel(writer, sheet_name='Parameter_Drift_Pct')
        
    print(f"\nDigester performance analysis saved to {output_file}")

if __name__ == "__main__":
    analyze_digester_performance('df_clustered_batches.xlsx', 'digester_performance_summary.xlsx')
