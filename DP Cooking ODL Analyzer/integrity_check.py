import pandas as pd
import numpy as np

def run_integrity_check():
    print("--- STARTING INTEGRITY CHECK ---")
    
    # Load files
    df_clustered = pd.read_excel('df_clustered_batches.xlsx')
    df_sop = pd.read_excel('sop_limits_reference.xlsx')
    df_final = pd.read_excel('final_variation_analysis.xlsx', sheet_name='SOP_Limits')
    
    # 1. Check SOP Limit Consistency
    # Pick a sample parameter that has data
    sample_param = 'Deknotting Feed Cons (%)'
    mean_col = sample_param + '_mean'
    
    normal_data = df_clustered[df_clustered['Status_Flag'] == 'Normal'][mean_col].dropna()
    calc_5 = normal_data.quantile(0.05)
    calc_95 = normal_data.quantile(0.95)
    
    sop_row = df_sop[df_sop['Parameter'] == sample_param].iloc[0]
    final_row = df_final[df_final['Parameter'] == sample_param].iloc[0]
    
    print(f"Check 1: SOP Limit Calculation for '{sample_param}'")
    print(f"  - Recalculated from Data (5th/95th): {calc_5:.4f} / {calc_95:.4f}")
    print(f"  - Values in 'sop_limits_reference': {sop_row['SOP_Lower_Limit (5th%)']:.4f} / {sop_row['SOP_Upper_Limit (95th%)']:.4f}")
    print(f"  - Values in 'final_variation_analysis': {final_row['SOP_Lower_Limit (5th%)']:.4f} / {final_row['SOP_Upper_Limit (95th%)']:.4f}")
    
    # 2. Check Violation Count Logic
    # Let's count violations for one batch manually
    batch_idx = 0
    batch = df_clustered.iloc[batch_idx]
    d_id = batch['Digester_ID']
    b_num = batch_idx + 1 # Assuming order was preserved
    
    # Load all violations sheet
    df_violations = pd.read_excel('final_variation_analysis.xlsx', sheet_name='All_Batch_Violations')
    reported_violations = df_violations[(df_violations['Digester_ID'] == d_id) & (df_violations['Batch_Number'] == b_num)]['SOP_Violation_Count'].values[0]
    
    # Manual check
    manual_violations = 0
    for _, row in df_sop.iterrows():
        p = row['Parameter'] + '_mean'
        if p in df_clustered.columns:
            val = batch[p]
            if pd.notnull(val):
                if val < row['SOP_Lower_Limit (5th%)'] or val > row['SOP_Upper_Limit (95th%)']:
                    manual_violations += 1
    
    print(f"\nCheck 2: Violation Count for Digester {d_id} Batch {b_num}")
    print(f"  - Reported in Final Analysis: {reported_violations}")
    print(f"  - Manually Calculated: {manual_violations}")
    
    # 3. Check Data Quality (Zero/Missing values)
    print(f"\nCheck 3: Data Quality")
    kappa_zeros = (df_clustered['Post O2 Kappa_Kappa online (%)_mean'] == 0).sum()
    print(f"  - Batches with 0.0 Kappa: {kappa_zeros} out of {len(df_clustered)}")

if __name__ == "__main__":
    run_integrity_check()
