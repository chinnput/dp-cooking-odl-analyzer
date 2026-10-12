import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

def analyze_and_visualize_consumption(input_file, output_img='Specific_Steam_Consumption_Comparison.png', output_xlsx='steam_consumption_analysis.xlsx'):
    print(f"Reading clustered data from {input_file}...")
    df = pd.read_excel(input_file)
    
    # 1. Clean data types for plotting
    df['Digester_ID'] = df['Digester_ID'].astype(int)
    df['Status_Flag'] = df['Status_Flag'].astype(str)
    
    mean_col = 'Specific Steam Consumption (t_ADT)_mean'
    std_col = 'Specific Steam Consumption (t_ADT)_std'
    
    # Check if columns exist
    if mean_col not in df.columns or std_col not in df.columns:
        print("Error: Specific steam consumption columns not found in dataset.")
        return
        
    # Drop rows where consumption is NaN
    valid_df = df[df[mean_col].notnull()].copy()
    print(f"Analyzing {len(valid_df)} batches with valid steam consumption data.")
    
    # 2. Compute Summary Statistics by Digester and Status Flag
    summary_stats = valid_df.groupby(['Digester_ID', 'Status_Flag']).agg(
        Batch_Count=(mean_col, 'count'),
        Avg_Specific_Steam_Consumption=(mean_col, 'mean'),
        Median_Specific_Steam_Consumption=(mean_col, 'median'),
        Std_Specific_Steam_Consumption=(mean_col, 'std'),
        Avg_Within_Batch_Volatility=(std_col, 'mean'),
        Median_Within_Batch_Volatility=(std_col, 'median')
    ).reset_index()
    
    print("\n--- SPECIFIC STEAM CONSUMPTION SUMMARY TABLE ---")
    print(summary_stats.to_string(index=False))
    
    # Save the summary statistics to Excel
    print(f"\nSaving statistical summary to {output_xlsx}...")
    summary_stats.to_excel(output_xlsx, index=False)
    
    # 3. Create High-Quality Visualization
    print(f"Generating comparison plot: {output_img}...")
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    fig.suptitle('Specific Steam Consumption Analysis: Normal vs. Abnormal Batches', fontsize=16, fontweight='bold', y=0.98)
    
    # Custom palette
    palette = {'Normal': '#2ca02c', 'Abnormal': '#d62728'}
    
    # Left Subplot: Specific Steam Consumption (Process Level)
    ax1 = axes[0]
    sns.boxplot(
        x='Digester_ID',
        y=mean_col,
        hue='Status_Flag',
        data=valid_df,
        palette=palette,
        ax=ax1,
        width=0.6,
        fliersize=0  # Hide fliers to show raw data points clearly with stripplot
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
    
    ax1.set_title('Specific Steam Consumption Average (t/ADT)', fontsize=13, fontweight='bold')
    ax1.set_xlabel('Digester ID', fontsize=11)
    ax1.set_ylabel('Specific Steam Consumption (t/ADT)', fontsize=11)
    ax1.grid(True, linestyle='--', alpha=0.5)
    ax1.set_ylim(0, 8.0)  # Capping y-axis so the core data (up to ~5.5) fits within 70% of the graph height
    
    # Right Subplot: Steam Consumption Volatility (Within-Batch Standard Deviation)
    ax2 = axes[1]
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
    
    ax2.set_title('Steam Consumption Within-Batch Volatility (SD)', fontsize=13, fontweight='bold')
    ax2.set_xlabel('Digester ID', fontsize=11)
    ax2.set_ylabel('Steam Consumption Std Dev (t/h)', fontsize=11)
    ax2.grid(True, linestyle='--', alpha=0.5)
    ax2.set_ylim(0, 8.0)  # Capping y-axis so the core volatility data (up to ~5.5) fits within 70% of the graph height
    
    # Add data labels directly onto the first plot for average and median consumption
    y_min, y_max = ax1.get_ylim()
    y_range = y_max - y_min
    
    for i, d_id in enumerate(sorted(valid_df['Digester_ID'].unique())):
        for status, color in [('Normal', '#2ca02c'), ('Abnormal', '#d62728')]:
            subset = summary_stats[(summary_stats['Digester_ID'] == d_id) & (summary_stats['Status_Flag'] == status)]
            if len(subset) > 0:
                avg_val = subset['Avg_Specific_Steam_Consumption'].values[0]
                med_val = subset['Median_Specific_Steam_Consumption'].values[0]
                n_val = subset['Batch_Count'].values[0]
                
                # Determine x position offsets based on dodge
                x_pos = i + (-0.15 if status == 'Normal' else 0.15)
                # Position text above the box plot to avoid overlapping and keep inside ylim
                if status == 'Normal':
                    text_y = y_min + (y_range * 0.08)
                else:
                    text_y = min(max(avg_val, med_val), y_max - (y_range * 0.25)) + (y_range * 0.04)
                
                stats_text = f"Mean: {avg_val:.3f}\nMed: {med_val:.3f}\nN={n_val}"
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

    # Add data labels directly onto the second plot for volatility
    y_min2, y_max2 = ax2.get_ylim()
    y_range2 = y_max2 - y_min2
    
    for i, d_id in enumerate(sorted(valid_df['Digester_ID'].unique())):
        for status, color in [('Normal', '#2ca02c'), ('Abnormal', '#d62728')]:
            subset = summary_stats[(summary_stats['Digester_ID'] == d_id) & (summary_stats['Status_Flag'] == status)]
            if len(subset) > 0:
                avg_vol = subset['Avg_Within_Batch_Volatility'].values[0]
                med_vol = subset['Median_Within_Batch_Volatility'].values[0]
                
                # Determine x position offsets based on dodge
                x_pos = i + (-0.15 if status == 'Normal' else 0.15)
                # Position text above the box plot to avoid overlapping and keep inside ylim
                if status == 'Normal':
                    text_y = y_min2 + (y_range2 * 0.08)
                else:
                    text_y = min(max(avg_vol, med_vol), y_max2 - (y_range2 * 0.25)) + (y_range2 * 0.04)
                
                stats_text = f"Mean: {avg_vol:.3f}\nMed: {med_vol:.3f}"
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
    
    # 4. Generate some interesting insights to print
    print("\n--- PROCESS INSIGHTS & INTERPRETATIONS ---")
    for d_id in sorted(valid_df['Digester_ID'].unique()):
        norm_row = summary_stats[(summary_stats['Digester_ID'] == d_id) & (summary_stats['Status_Flag'] == 'Normal')]
        abnorm_row = summary_stats[(summary_stats['Digester_ID'] == d_id) & (summary_stats['Status_Flag'] == 'Abnormal')]
        
        if len(norm_row) > 0 and len(abnorm_row) > 0:
            norm_avg = norm_row['Avg_Specific_Steam_Consumption'].values[0]
            abnorm_avg = abnorm_row['Avg_Specific_Steam_Consumption'].values[0]
            diff_pct = ((abnorm_avg - norm_avg) / norm_avg) * 100
            
            print(f"Digester {d_id}:")
            print(f"  - Normal Batches Specific Steam Consumption: {norm_avg:.4f} t/ADT")
            print(f"  - Abnormal Batches Specific Steam Consumption: {abnorm_avg:.4f} t/ADT")
            print(f"  - Change: {diff_pct:+.2f}% during abnormal operations.")
            
            norm_vol = norm_row['Avg_Within_Batch_Volatility'].values[0]
            abnorm_vol = abnorm_row['Avg_Within_Batch_Volatility'].values[0]
            vol_diff_pct = ((abnorm_vol - norm_vol) / norm_vol) * 100
            print(f"  - Normal Within-Batch Volatility (SD): {norm_vol:.4f} t/h")
            print(f"  - Abnormal Within-Batch Volatility (SD): {abnorm_vol:.4f} t/h")
            print(f"  - Volatility Change: {vol_diff_pct:+.2f}%")
            print()

if __name__ == "__main__":
    analyze_and_visualize_consumption('df_clustered_batches.xlsx')
