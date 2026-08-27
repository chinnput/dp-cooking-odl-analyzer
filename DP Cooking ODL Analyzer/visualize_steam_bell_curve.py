import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

def generate_steam_bell_curve(clustered_file, limits_file, output_img='visualizations_bell/Specific_Steam_Consumption_Bell_Curve.png'):
    print(f"Reading clustered data from {clustered_file}...")
    df = pd.read_excel(clustered_file)
    df_limits = pd.read_excel(limits_file)
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_img)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    param_col = 'Specific Steam Consumption (t_ADT)_mean'
    
    # Retrieve SOP limits for Specific Steam Consumption
    limit_row = df_limits[df_limits['Parameter'] == 'Specific Steam Consumption (t_ADT)'].iloc[0]
    low_lim = limit_row['SOP_Lower_Limit (5th%)']
    target_val = limit_row['SOP_Target (Mean)']
    high_lim = limit_row['SOP_Upper_Limit (95th%)']
    std_lim = limit_row['SOP_Std_Dev (Stability)']
    
    # Filter for non-null data
    valid_df = df[df[param_col].notnull()].copy()
    normal_data = valid_df[valid_df['Status_Flag'] == 'Normal'][param_col]
    abnormal_data = valid_df[valid_df['Status_Flag'] == 'Abnormal'][param_col]
    
    plt.figure(figsize=(12, 7))
    
    # 1. Plot KDE (Bell Curve) distributions
    # We use a slight clipping/limitation of range for plotting stability, and adjust bandwidth
    sns.kdeplot(
        normal_data, 
        fill=True, 
        color='#2ca02c', 
        label=f'Normal Batches (SOP Base, N={len(normal_data)})', 
        alpha=0.4, 
        bw_adjust=1.2
    )
    sns.kdeplot(
        abnormal_data, 
        fill=True, 
        color='#d62728', 
        label=f'Abnormal Batches (Wastage Base, N={len(abnormal_data)})', 
        alpha=0.4, 
        bw_adjust=1.2
    )
    
    # 2. Draw SOP limits vertical dashed lines
    plt.axvline(low_lim, color='darkgreen', linestyle=':', linewidth=2, label=f'SOP Lower Limit (5th%): {low_lim:.3f} t/ADT')
    plt.axvline(target_val, color='blue', linestyle='--', linewidth=2.5, label=f'SOP Target (Mean): {target_val:.3f} t/ADT')
    plt.axvline(high_lim, color='darkorange', linestyle=':', linewidth=2, label=f'SOP Upper Limit (95th%): {high_lim:.3f} t/ADT')
    
    # 3. Add text labels with exact statistics
    stats_text = (
        f"NORMAL STATE:\n"
        f"  • Mean: {normal_data.mean():.4f} t/ADT\n"
        f"  • Median: {normal_data.median():.4f} t/ADT\n"
        f"  • Std Dev: {normal_data.std():.4f} t/ADT\n\n"
        f"ABNORMAL STATE:\n"
        f"  • Mean: {abnormal_data.mean():.4f} t/ADT\n"
        f"  • Median: {abnormal_data.median():.4f} t/ADT\n"
        f"  • Std Dev: {abnormal_data.std():.4f} t/ADT\n"
        f"  • Consumption Increase: +{((abnormal_data.mean() - normal_data.mean()) / normal_data.mean() * 100):.1f}%"
    )
    
    plt.text(
        0.97, 0.93, 
        stats_text, 
        transform=plt.gca().transAxes, 
        fontsize=10, 
        fontweight='bold',
        verticalalignment='top', 
        horizontalalignment='right', 
        bbox=dict(boxstyle='round,pad=0.4', facecolor='white', alpha=0.9, edgecolor='gray')
    )
    
    # Set labels, grid, and title
    plt.title('Specific Steam Consumption Distribution comparison: Normal vs. Abnormal', fontsize=15, fontweight='bold', pad=15)
    plt.xlabel('Specific Steam Consumption (t/ADT)', fontsize=12, fontweight='bold')
    plt.ylabel('Probability Density', fontsize=12, fontweight='bold')
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.legend(loc='upper left', fontsize=10)
    
    # Cap X-axis at 2.0 to display the core "bell" curve region and keep data within 70% of graph height/width
    plt.xlim(-0.1, 2.0)
    
    # Set y limit with a little headroom
    y_min, y_max = plt.gca().get_ylim()
    plt.ylim(0, y_max * 1.15)
    
    plt.tight_layout()
    plt.savefig(output_img, dpi=150)
    plt.close()
    print(f"Steam bell curve successfully saved to {output_img}")

if __name__ == "__main__":
    generate_steam_bell_curve('df_clustered_batches.xlsx', 'sop_limits_reference.xlsx')
