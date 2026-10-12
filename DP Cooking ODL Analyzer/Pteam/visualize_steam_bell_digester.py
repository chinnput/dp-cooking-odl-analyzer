import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

def generate_steam_bell_digester(input_file, output_img='visualizations_digester/Specific_Steam_Consumption_t_ADT_bell_curves.png'):
    print(f"Reading clustered data from {input_file}...")
    df = pd.read_excel(input_file)
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_img)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    mean_col = 'Specific Steam Consumption (t_ADT)_mean'
    std_col = 'Specific Steam Consumption (t_ADT)_std'
    
    # Check if columns exist
    if mean_col not in df.columns or std_col not in df.columns:
        print("Error: Specific steam consumption columns not found.")
        return
        
    # Clean data types
    df['Digester_ID'] = df['Digester_ID'].astype(int)
    valid_df = df[df[mean_col].notnull() & df[std_col].notnull()].copy()
    
    fig, axes = plt.subplots(1, 2, figsize=(16, 8))
    fig.suptitle('Digester Comparison: Specific Steam Consumption Distribution (Bell Curves)', fontsize=16, fontweight='bold', y=0.98)
    
    # Color palette for Digesters 1-4
    palette = {1: '#1f77b4', 2: '#ff7f0e', 3: '#2ca02c', 4: '#d62728'}
    names = {1: 'Digester 1 (D1)', 2: 'Digester 2 (D2)', 3: 'Digester 3 (D3)', 4: 'Digester 4 (D4)'}
    
    # ------------- SUBPLOT 1: BATCH MEANS (Bell Curves) -------------
    ax1 = axes[0]
    for d_id in sorted(valid_df['Digester_ID'].unique()):
        d_data = valid_df[valid_df['Digester_ID'] == d_id][mean_col]
        sns.kdeplot(
            d_data,
            fill=True,
            color=palette[d_id],
            label=f'{names[d_id]} (N={len(d_data)})',
            alpha=0.25,
            linewidth=2,
            ax=ax1,
            bw_adjust=1.3
        )
        
    ax1.set_title('Batch Average Values (Process Level)', fontsize=13, fontweight='bold')
    ax1.set_xlabel('Specific Steam Consumption (t/ADT)', fontsize=11)
    ax1.set_ylabel('Probability Density', fontsize=11)
    ax1.set_xlim(-0.1, 2.0)  # Cap x-axis to fit within 70% of the height and show the bell curves clearly
    ax1.grid(True, linestyle='--', alpha=0.5)
    
    # Add stats labels onto Left Plot
    stats_text1 = "BATCH MEANS STATS:\n"
    for d_id in sorted(valid_df['Digester_ID'].unique()):
        d_data = valid_df[valid_df['Digester_ID'] == d_id][mean_col]
        stats_text1 += f"  • D{d_id}: Mean={d_data.mean():.3f}, Med={d_data.median():.3f}\n"
        
    ax1.text(
        0.95, 0.95, 
        stats_text1.strip(), 
        transform=ax1.transAxes, 
        fontsize=9, 
        fontweight='bold',
        verticalalignment='top', 
        horizontalalignment='right', 
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.85, edgecolor='gray')
    )
    ax1.legend(loc='upper left', fontsize=9)
    
    # ------------- SUBPLOT 2: WITHIN-BATCH VOLATILITY (Bell Curves) -------------
    ax2 = axes[1]
    for d_id in sorted(valid_df['Digester_ID'].unique()):
        d_data = valid_df[valid_df['Digester_ID'] == d_id][std_col]
        sns.kdeplot(
            d_data,
            fill=True,
            color=palette[d_id],
            label=f'{names[d_id]}',
            alpha=0.25,
            linewidth=2,
            ax=ax2,
            bw_adjust=1.3
        )
        
    ax2.set_title('Within-Batch Volatility (Process Instability)', fontsize=13, fontweight='bold')
    ax2.set_xlabel('Steam Consumption Volatility SD (t/h)', fontsize=11)
    ax2.set_ylabel('Probability Density', fontsize=11)
    ax2.set_xlim(-0.1, 2.0)  # Cap x-axis to zoom in on volatility distributions
    ax2.grid(True, linestyle='--', alpha=0.5)
    
    # Add stats labels onto Right Plot
    stats_text2 = "VOLATILITY STATS (SD):\n"
    for d_id in sorted(valid_df['Digester_ID'].unique()):
        d_data = valid_df[valid_df['Digester_ID'] == d_id][std_col]
        stats_text2 += f"  • D{d_id}: Mean={d_data.mean():.3f}, Med={d_data.median():.3f}\n"
        
    ax2.text(
        0.95, 0.95, 
        stats_text2.strip(), 
        transform=ax2.transAxes, 
        fontsize=9, 
        fontweight='bold',
        verticalalignment='top', 
        horizontalalignment='right', 
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.85, edgecolor='gray')
    )
    ax2.legend(loc='upper left', fontsize=9)
    
    # Adjust headroom so that peak data is within 70% of height
    y_min1, y_max1 = ax1.get_ylim()
    ax1.set_ylim(0, y_max1 * 1.2)
    y_min2, y_max2 = ax2.get_ylim()
    ax2.set_ylim(0, y_max2 * 1.2)
    
    plt.tight_layout()
    plt.savefig(output_img, dpi=150)
    plt.close()
    print(f"Digester bell curve comparison saved to {output_img}")

if __name__ == "__main__":
    generate_steam_bell_digester('df_clustered_batches.xlsx')
