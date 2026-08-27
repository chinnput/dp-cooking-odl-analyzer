import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

def generate_chemical_bell_digester(input_file, output_img='visualizations_digester/Specific_Chemical_Consumption_bell_curves.png'):
    print(f"Reading clustered data from {input_file}...")
    df = pd.read_excel(input_file)
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_img)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    df['Digester_ID'] = df['Digester_ID'].astype(int)
    
    # Define chemicals parameters
    chemicals = [
        {
            'name': 'Specific WHLiqu Consumption',
            'mean_col': 'Specific WHLiqu Consumption (m3_ADT)_mean',
            'std_col': 'Specific WHLiqu Consumption (m3_ADT)_std',
            'unit': 'm3/ADT',
            'vol_unit': 'm3/h',
            'xlim': 3.0,
            'title_label': 'White Liquor'
        },
        {
            'name': 'Specific O2 Mixer 1 Consumption',
            'mean_col': 'Specific O2 Mixer 1 Consumption (kg_ADT)_mean',
            'std_col': 'Specific O2 Mixer 1 Consumption (kg_ADT)_std',
            'unit': 'kg/ADT',
            'vol_unit': 'kg/h',
            'xlim': 250.0,
            'title_label': 'Oxygen Mixer 1'
        },
        {
            'name': 'Specific O2 Pulp Heater Consumption',
            'mean_col': 'Specific O2 Pulp Heater Consumption (kg_ADT)_mean',
            'std_col': 'Specific O2 Pulp Heater Consumption (kg_ADT)_std',
            'unit': 'kg/ADT',
            'vol_unit': 'kg/h',
            'xlim': 250.0,
            'title_label': 'Oxygen Pulp Heater'
        }
    ]
    
    fig, axes = plt.subplots(3, 2, figsize=(16, 20))
    fig.suptitle('Digester Comparison: Specific Chemical Consumption Distributions (Bell Curves)', fontsize=18, fontweight='bold', y=0.99)
    
    palette = {1: '#1f77b4', 2: '#ff7f0e', 3: '#2ca02c', 4: '#d62728'}
    names = {1: 'D1', 2: 'D2', 3: 'D3', 4: 'D4'}
    
    for row_idx, chem in enumerate(chemicals):
        mean_col = chem['mean_col']
        std_col = chem['std_col']
        xlim_val = chem['xlim']
        
        # Filter non-null data
        valid_df = df[df[mean_col].notnull() & df[std_col].notnull()].copy()
        
        # ------------- LEFT SUBPLOT: BATCH MEANS -------------
        ax1 = axes[row_idx, 0]
        for d_id in sorted(valid_df['Digester_ID'].unique()):
            d_data = valid_df[valid_df['Digester_ID'] == d_id][mean_col]
            sns.kdeplot(
                d_data,
                fill=True,
                color=palette[d_id],
                label=f'Digester {d_id} (N={len(d_data)})',
                alpha=0.20,
                linewidth=1.8,
                ax=ax1,
                bw_adjust=1.3
            )
            
        ax1.set_title(f'{chem["title_label"]} Specific Consumption Average ({chem["unit"]})', fontsize=12, fontweight='bold')
        ax1.set_xlabel(f'Specific Consumption ({chem["unit"]})', fontsize=10)
        ax1.set_ylabel('Probability Density', fontsize=10)
        ax1.set_xlim(-0.05 * xlim_val, xlim_val)
        ax1.grid(True, linestyle='--', alpha=0.5)
        
        # Add stats text box
        stats_text1 = "BATCH MEANS STATS:\n"
        for d_id in sorted(valid_df['Digester_ID'].unique()):
            d_data = valid_df[valid_df['Digester_ID'] == d_id][mean_col]
            stats_text1 += f"  • D{d_id}: Mean={d_data.mean():.2f}, Med={d_data.median():.2f}\n"
            
        ax1.text(
            0.95, 0.95, 
            stats_text1.strip(), 
            transform=ax1.transAxes, 
            fontsize=8, 
            fontweight='bold',
            verticalalignment='top', 
            horizontalalignment='right', 
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.85, edgecolor='gray')
        )
        ax1.legend(loc='upper left', fontsize=8)
        
        # ------------- RIGHT SUBPLOT: WITHIN-BATCH VOLATILITY -------------
        ax2 = axes[row_idx, 1]
        for d_id in sorted(valid_df['Digester_ID'].unique()):
            d_data = valid_df[valid_df['Digester_ID'] == d_id][std_col]
            sns.kdeplot(
                d_data,
                fill=True,
                color=palette[d_id],
                label=f'Digester {d_id}',
                alpha=0.20,
                linewidth=1.8,
                ax=ax2,
                bw_adjust=1.3
            )
            
        ax2.set_title(f'{chem["title_label"]} Flow Within-Batch Volatility ({chem["vol_unit"]})', fontsize=12, fontweight='bold')
        ax2.set_xlabel(f'Flow Volatility SD ({chem["vol_unit"]})', fontsize=10)
        ax2.set_ylabel('Probability Density', fontsize=10)
        ax2.set_xlim(-0.05 * xlim_val, xlim_val)
        ax2.grid(True, linestyle='--', alpha=0.5)
        
        # Add stats text box
        stats_text2 = "VOLATILITY STATS (SD):\n"
        for d_id in sorted(valid_df['Digester_ID'].unique()):
            d_data = valid_df[valid_df['Digester_ID'] == d_id][std_col]
            stats_text2 += f"  • D{d_id}: Mean={d_data.mean():.2f}, Med={d_data.median():.2f}\n"
            
        ax2.text(
            0.95, 0.95, 
            stats_text2.strip(), 
            transform=ax2.transAxes, 
            fontsize=8, 
            fontweight='bold',
            verticalalignment='top', 
            horizontalalignment='right', 
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.85, edgecolor='gray')
        )
        ax2.legend(loc='upper left', fontsize=8)
        
        # Adjust headroom so that peak data fits within 70% of height
        y_min1, y_max1 = ax1.get_ylim()
        ax1.set_ylim(0, y_max1 * 1.25)
        y_min2, y_max2 = ax2.get_ylim()
        ax2.set_ylim(0, y_max2 * 1.25)

    plt.tight_layout()
    plt.savefig(output_img, dpi=150)
    plt.close()
    print(f"Chemical bell curve comparison saved to {output_img}")

if __name__ == "__main__":
    generate_chemical_bell_digester('df_clustered_batches.xlsx')
