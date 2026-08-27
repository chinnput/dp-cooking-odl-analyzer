import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

def analyze_and_visualize_chemicals(input_file, output_img='Specific_Chemical_Consumption_Comparison.png', output_xlsx='chemical_consumption_analysis.xlsx'):
    print(f"Reading clustered data from {input_file}...")
    df = pd.read_excel(input_file)
    
    # 1. Clean data types for plotting
    df['Digester_ID'] = df['Digester_ID'].astype(int)
    df['Status_Flag'] = df['Status_Flag'].astype(str)
    
    # Define parameters
    chemicals = [
        {
            'name': 'Specific WHLiqu Consumption',
            'mean_col': 'Specific WHLiqu Consumption (m3_ADT)_mean',
            'std_col': 'Specific WHLiqu Consumption (m3_ADT)_std',
            'unit': 'm3/ADT',
            'vol_unit': 'm3/h',
            'ylim': 3.0,
            'title_label': 'White Liquor'
        },
        {
            'name': 'Specific O2 Mixer 1 Consumption',
            'mean_col': 'Specific O2 Mixer 1 Consumption (kg_ADT)_mean',
            'std_col': 'Specific O2 Mixer 1 Consumption (kg_ADT)_std',
            'unit': 'kg/ADT',
            'vol_unit': 'kg/h',
            'ylim': 250.0,
            'title_label': 'Oxygen Mixer 1'
        },
        {
            'name': 'Specific O2 Pulp Heater Consumption',
            'mean_col': 'Specific O2 Pulp Heater Consumption (kg_ADT)_mean',
            'std_col': 'Specific O2 Pulp Heater Consumption (kg_ADT)_std',
            'unit': 'kg/ADT',
            'vol_unit': 'kg/h',
            'ylim': 250.0,
            'title_label': 'Oxygen Pulp Heater'
        }
    ]
    
    summary_list = []
    
    # 2. Compute Summary Statistics for all chemicals
    print("\nComputing chemical specific consumption statistics...")
    for chem in chemicals:
        mean_col = chem['mean_col']
        std_col = chem['std_col']
        
        if mean_col not in df.columns or std_col not in df.columns:
            print(f"Warning: Columns for {chem['name']} not found in dataset.")
            continue
            
        valid_df = df[df[mean_col].notnull()].copy()
        
        chem_summary = valid_df.groupby(['Digester_ID', 'Status_Flag']).agg(
            Batch_Count=(mean_col, 'count'),
            Avg_Specific_Consumption=(mean_col, 'mean'),
            Median_Specific_Consumption=(mean_col, 'median'),
            Std_Specific_Consumption=(mean_col, 'std'),
            Avg_Volatility=(std_col, 'mean'),
            Median_Volatility=(std_col, 'median')
        ).reset_index()
        
        chem_summary['Chemical'] = chem['title_label']
        summary_list.append(chem_summary)
        
    if len(summary_list) == 0:
        print("Error: No valid chemical consumption data found to analyze.")
        return
        
    df_summary = pd.concat(summary_list, ignore_index=True)
    
    # Save statistics to Excel
    print(f"Saving chemical statistical summary to {output_xlsx}...")
    df_summary.to_excel(output_xlsx, index=False)
    
    # 3. Create High-Quality 3x2 Grid Plot
    print(f"Generating comparison plot: {output_img}...")
    fig, axes = plt.subplots(3, 2, figsize=(16, 20))
    fig.suptitle('Specific Chemical Consumption Analysis: Normal vs. Abnormal Batches', fontsize=18, fontweight='bold', y=0.99)
    
    palette = {'Normal': '#2ca02c', 'Abnormal': '#d62728'}
    
    for row_idx, chem in enumerate(chemicals):
        mean_col = chem['mean_col']
        std_col = chem['std_col']
        ylim_val = chem['ylim']
        
        # Filter data
        valid_df = df[df[mean_col].notnull() & df[std_col].notnull()].copy()
        chem_summary = df_summary[df_summary['Chemical'] == chem['title_label']]
        
        # Left Subplot: Average Specific Consumption
        ax1 = axes[row_idx, 0]
        sns.boxplot(
            x='Digester_ID',
            y=mean_col,
            hue='Status_Flag',
            data=valid_df,
            palette=palette,
            ax=ax1,
            width=0.6,
            fliersize=0
        )
        sns.stripplot(
            x='Digester_ID',
            y=mean_col,
            hue='Status_Flag',
            data=valid_df,
            palette=palette,
            dodge=True,
            ax=ax1,
            color='black',
            alpha=0.15,
            size=3,
            legend=False
        )
        
        ax1.set_title(f'{chem["title_label"]} Specific Consumption ({chem["unit"]})', fontsize=12, fontweight='bold')
        ax1.set_xlabel('Digester ID', fontsize=10)
        ax1.set_ylabel(f'Specific Consumption ({chem["unit"]})', fontsize=10)
        ax1.grid(True, linestyle='--', alpha=0.5)
        ax1.set_ylim(0, ylim_val)  # Set capped y-limit to zoom in and focus
        
        # Add data labels for subplot 1
        y_min1, y_max1 = ax1.get_ylim()
        y_range1 = y_max1 - y_min1
        
        for i, d_id in enumerate(sorted(valid_df['Digester_ID'].unique())):
            for status, color in [('Normal', '#2ca02c'), ('Abnormal', '#d62728')]:
                subset = chem_summary[(chem_summary['Digester_ID'] == d_id) & (chem_summary['Status_Flag'] == status)]
                if len(subset) > 0:
                    avg_val = subset['Avg_Specific_Consumption'].values[0]
                    med_val = subset['Median_Specific_Consumption'].values[0]
                    n_val = subset['Batch_Count'].values[0]
                    
                    x_pos = i + (-0.15 if status == 'Normal' else 0.15)
                    if status == 'Normal':
                        text_y = y_min1 + (y_range1 * 0.08)
                    else:
                        text_y = min(max(avg_val, med_val), y_max1 - (y_range1 * 0.25)) + (y_range1 * 0.04)
                    
                    stats_text = f"Mean: {avg_val:.2f}\nMed: {med_val:.2f}\nN={n_val}"
                    ax1.text(
                        x_pos, 
                        text_y, 
                        stats_text, 
                        ha='center', 
                        va='bottom', 
                        fontsize=8, 
                        fontweight='bold', 
                        color=color,
                        bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.9, edgecolor=color)
                    )
                    
        # Right Subplot: Volatility (Std Dev)
        ax2 = axes[row_idx, 1]
        sns.boxplot(
            x='Digester_ID',
            y=std_col,
            hue='Status_Flag',
            data=valid_df,
            palette=palette,
            ax=ax2,
            width=0.6,
            fliersize=0
        )
        sns.stripplot(
            x='Digester_ID',
            y=std_col,
            hue='Status_Flag',
            data=valid_df,
            palette=palette,
            dodge=True,
            ax=ax2,
            color='black',
            alpha=0.15,
            size=3,
            legend=False
        )
        
        ax2.set_title(f'{chem["title_label"]} Flow Within-Batch Volatility ({chem["vol_unit"]})', fontsize=12, fontweight='bold')
        ax2.set_xlabel('Digester ID', fontsize=10)
        ax2.set_ylabel(f'Flow Std Dev ({chem["vol_unit"]})', fontsize=10)
        ax2.grid(True, linestyle='--', alpha=0.5)
        ax2.set_ylim(0, ylim_val)  # Set capped y-limit to zoom in and focus
        
        # Add data labels for subplot 2
        y_min2, y_max2 = ax2.get_ylim()
        y_range2 = y_max2 - y_min2
        
        for i, d_id in enumerate(sorted(valid_df['Digester_ID'].unique())):
            for status, color in [('Normal', '#2ca02c'), ('Abnormal', '#d62728')]:
                subset = chem_summary[(chem_summary['Digester_ID'] == d_id) & (chem_summary['Status_Flag'] == status)]
                if len(subset) > 0:
                    avg_vol = subset['Avg_Volatility'].values[0]
                    med_vol = subset['Median_Volatility'].values[0]
                    
                    x_pos = i + (-0.15 if status == 'Normal' else 0.15)
                    if status == 'Normal':
                        text_y = y_min2 + (y_range2 * 0.08)
                    else:
                        text_y = min(max(avg_vol, med_vol), y_max2 - (y_range2 * 0.25)) + (y_range2 * 0.04)
                    
                    stats_text = f"Mean: {avg_vol:.2f}\nMed: {med_vol:.2f}"
                    ax2.text(
                        x_pos, 
                        text_y, 
                        stats_text, 
                        ha='center', 
                        va='bottom', 
                        fontsize=8, 
                        fontweight='bold', 
                        color=color,
                        bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.9, edgecolor=color)
                    )

    plt.tight_layout()
    plt.savefig(output_img, dpi=150)
    plt.close()
    print(f"Plot successfully saved to {output_img}")
    
    # 4. Generate Process Insights
    print("\n--- CHEMICAL PROCESS INSIGHTS & INTERPRETATIONS ---")
    for chem in chemicals:
        print(f"\n{chem['title_label'].upper()}:")
        chem_summary = df_summary[df_summary['Chemical'] == chem['title_label']]
        
        for d_id in sorted(df['Digester_ID'].unique()):
            norm_row = chem_summary[(chem_summary['Digester_ID'] == d_id) & (chem_summary['Status_Flag'] == 'Normal')]
            abnorm_row = chem_summary[(chem_summary['Digester_ID'] == d_id) & (chem_summary['Status_Flag'] == 'Abnormal')]
            
            if len(norm_row) > 0 and len(abnorm_row) > 0:
                norm_avg = norm_row['Avg_Specific_Consumption'].values[0]
                abnorm_avg = abnorm_row['Avg_Specific_Consumption'].values[0]
                diff_pct = ((abnorm_avg - norm_avg) / norm_avg) * 100
                
                norm_vol = norm_row['Avg_Volatility'].values[0]
                abnorm_vol = abnorm_row['Avg_Volatility'].values[0]
                vol_diff_pct = ((abnorm_vol - norm_vol) / norm_vol) * 100
                
                print(f"  Digester {d_id}:")
                print(f"    - Specific Consumption (Normal vs Abnormal): {norm_avg:.3f} vs {abnorm_avg:.3f} {chem['unit']} ({diff_pct:+.1f}%)")
                print(f"    - Flow Volatility SD (Normal vs Abnormal): {norm_vol:.3f} vs {abnorm_vol:.3f} {chem['vol_unit']} ({vol_diff_pct:+.1f}%)")

if __name__ == "__main__":
    analyze_and_visualize_chemicals('df_clustered_batches.xlsx')
