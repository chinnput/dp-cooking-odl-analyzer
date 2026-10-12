import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import seaborn as sns

def analyze_process_variations(signatures_file, limits_file, output_file):
    """
    Consolidated analysis of batch-wise process variations and SOP violations.
    """
    print(f"Loading data: {signatures_file} and {limits_file}")
    df_batches = pd.read_excel(signatures_file)
    df_limits = pd.read_excel(limits_file)

    # 1. PREPARATION: Assign Batch Numbers
    df_batches = df_batches.sort_values(['Digester_ID', 'Start_Time'])
    df_batches['Batch_Number'] = df_batches.groupby('Digester_ID').cumcount() + 1

    # 2. ANALYSIS: Batch Violation Counts
    print("Calculating SOP violations per batch...")
    limits_lookup = {
        row['Parameter'] + "_mean": {
            'low': row['SOP_Lower_Limit (5th%)'],
            'high': row['SOP_Upper_Limit (95th%)'],
            'std_target': row['SOP_Std_Dev (Stability)']
        } for _, row in df_limits.iterrows()
    }

    violation_results = []
    for idx, batch in df_batches.iterrows():
        violations = 0
        total_checked = 0
        unstable = 0
        for param, lims in limits_lookup.items():
            if param in df_batches.columns:
                val = batch[param]
                if pd.notnull(val):
                    total_checked += 1
                    if val < lims['low'] or val > lims['high']:
                        violations += 1
                
                std_col = param.replace('_mean', '_std')
                if std_col in df_batches.columns:
                    std_val = batch[std_col]
                    if pd.notnull(std_val) and std_val > lims['std_target']:
                        unstable += 1
        
        violation_results.append({
            'Digester_ID': batch['Digester_ID'],
            'Batch_Number': batch['Batch_Number'],
            'Start_Time': batch['Start_Time'],
            'SOP_Violation_Count': violations,
            'Unstable_Parameter_Count': unstable,
            'Violation_Pct': (violations / total_checked * 100) if total_checked > 0 else 0
        })
    df_batch_violations = pd.DataFrame(violation_results)

    # 3. ANALYSIS: Parameter Violation Leaders (Extreme Deviations)
    print("Identifying extreme offenders per parameter...")
    extreme_results = []
    for _, row in df_limits.iterrows():
        param = row['Parameter']
        mean_col = param + "_mean"
        if mean_col in df_batches.columns:
            low, high = row['SOP_Lower_Limit (5th%)'], row['SOP_Upper_Limit (95th%)']
            valid = df_batches[df_batches[mean_col].notnull()].copy()
            
            if len(valid) > 0:
                valid['Dev'] = valid[mean_col].apply(lambda x: max(0, low - x, x - high))
                worst = valid.loc[valid['Dev'].idxmax()]
                if worst['Dev'] > 0:
                    extreme_results.append({
                        'Parameter': param,
                        'SOP_Range': f"{low:.2f} - {high:.2f}",
                        'Worst_Batch': f"Digester {int(worst['Digester_ID'])} Batch {int(worst['Batch_Number'])}",
                        'Value': worst[mean_col],
                        'Deviation': worst['Dev'],
                        'Direction': 'High' if worst[mean_col] > high else 'Low'
                    })
    df_param_leaders = pd.DataFrame(extreme_results).sort_values('Deviation', ascending=False)

    # 4. ANALYSIS: Digester-Parameter Performance & Heatmap Data
    print("Analyzing which digester is out of bounds most per parameter...")
    heatmap_data = []
    digester_param_results = []
    
    for _, row in df_limits.iterrows():
        param = row['Parameter']
        mean_col = param + "_mean"
        if mean_col in df_batches.columns:
            low, high = row['SOP_Lower_Limit (5th%)'], row['SOP_Upper_Limit (95th%)']
            
            # Identify all violations for this parameter
            df_batches['Is_Violating'] = df_batches[mean_col].apply(lambda x: 1 if pd.notnull(x) and (x < low or x > high) else 0)
            
            # Group by Digester to see who violates most
            stats = df_batches.groupby('Digester_ID').agg(
                Violations=('Is_Violating', 'sum'),
                Total=('Is_Violating', 'count')
            )
            stats['Rate'] = (stats['Violations'] / stats['Total'] * 100).fillna(0)
            
            # Store for heatmap (Param vs Digester)
            for d_id, r in stats['Rate'].items():
                heatmap_data.append({'Parameter': param, 'Digester': f"D{int(d_id)}", 'Violation_Rate': r})

            # Find the worst digester summary
            worst_id = stats['Rate'].idxmax()
            if stats.loc[worst_id, 'Violations'] > 0:
                digester_param_results.append({
                    'Parameter': param,
                    'Worst_Digester': f"Digester {int(worst_id)}",
                    'Violation_Count': stats.loc[worst_id, 'Violations'],
                    'Violation_Rate_Pct': stats.loc[worst_id, 'Rate'],
                    'Total_Batches': stats.loc[worst_id, 'Total']
                })
                
    df_digester_param = pd.DataFrame(digester_param_results).sort_values('Violation_Rate_Pct', ascending=False)
    
    # 5. VISUALIZATION: Heatmap
    print("Generating Heatmap visualization...")
    df_heatmap = pd.DataFrame(heatmap_data).pivot(index='Parameter', columns='Digester', values='Violation_Rate')
    
    plt.figure(figsize=(12, 16))
    sns.heatmap(df_heatmap, annot=True, fmt=".1f", cmap="YlOrRd", cbar_kws={'label': 'Violation Rate (%)'})
    plt.title('Process Variation Heatmap: SOP Violation Rate % by Digester', fontsize=16)
    plt.tight_layout()
    plt.savefig('digester_performance_heatmap.png')
    plt.close()

    # 6. EXPORT: Save to Excel
    print(f"Saving final report to {output_file}...")
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df_limits.to_excel(writer, sheet_name='SOP_Limits', index=False)
        df_batch_violations.to_excel(writer, sheet_name='All_Batch_Violations', index=False)
        df_param_leaders.to_excel(writer, sheet_name='Parameter_Violation_Leaders', index=False)
        df_digester_param.to_excel(writer, sheet_name='Digester_Parameter_Performance', index=False)
    
    print("Success: Analysis and Heatmap complete.")
    
    print("Success: Analysis complete.")

if __name__ == "__main__":
    # Input files
    SIG_FILE = 'df_clustered_batches.xlsx'
    LIM_FILE = 'sop_limits_reference.xlsx'
    OUT_FILE = 'final_variation_analysis.xlsx'
    
    if os.path.exists(SIG_FILE) and os.path.exists(LIM_FILE):
        analyze_process_variations(SIG_FILE, LIM_FILE, OUT_FILE)
    else:
        print("Error: Required input files not found.")
