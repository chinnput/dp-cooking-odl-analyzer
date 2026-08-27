import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np

def visualize_bell_curves_with_limits(input_file, output_dir='visualizations_bell'):
    print(f"Reading clustered data from {input_file}...")
    df = pd.read_excel(input_file)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    important_params = [
        'Deknotting Feed Flow (m3/h)_mean',
        'Screening Accept flow (m3/h)_mean',
        'Production ODL (ADT/D)_mean',
        'O2 to Mixer1_Oxygen feed at Reactor 1 (kg/h)_mean',
        'Press 1 Feed Cons (%)_mean'
    ]
    
    print(f"Generating bell curves with SOP limits...")
    
    for param in important_params:
        plt.figure(figsize=(12, 7))
        
        # Plot KDE
        sns.kdeplot(data=df[df['Status_Flag'] == 'Normal'], x=param, fill=True, color='green', label='Normal (SOP)', alpha=0.4)
        sns.kdeplot(data=df[df['Status_Flag'] == 'Abnormal'], x=param, fill=True, color='red', label='Abnormal', alpha=0.4)
        
        # Calculate SOP Limits based on the Normal group (5th and 95th percentile)
        # This defines the "Normal Operating Window"
        lower_limit = df[df['Status_Flag'] == 'Normal'][param].quantile(0.05)
        upper_limit = df[df['Status_Flag'] == 'Normal'][param].quantile(0.95)
        
        # Add vertical lines for SOP Limits
        plt.axvline(lower_limit, color='darkgreen', linestyle='--', linewidth=2, label=f'SOP Lower Limit ({lower_limit:.2f})')
        plt.axvline(upper_limit, color='darkgreen', linestyle='--', linewidth=2, label=f'SOP Upper Limit ({upper_limit:.2f})')
        
        # Label the Abnormal area
        plt.title(f'SOP Limits & Process Variation: {param}', fontsize=14)
        
        # Stats box
        stats = df.groupby('Status_Flag')[param].agg(['mean', 'std'])
        text_str = (
            f"SOP WINDOW (Normal):\n"
            f"Low: {lower_limit:.2f} | High: {upper_limit:.2f}\n\n"
            f"ABNORMAL STATS:\n"
            f"Mean: {stats.loc['Abnormal', 'mean']:.2f}\n"
            f"Std: {stats.loc['Abnormal', 'std']:.2f}"
        )
        
        plt.text(0.05, 0.95, text_str, transform=plt.gca().transAxes, fontsize=11,
                 verticalalignment='top', horizontalalignment='left', 
                 bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        plt.xlabel(param, fontsize=12)
        plt.ylabel('Density', fontsize=12)
        plt.legend(loc='upper right')
        plt.grid(True, alpha=0.2)
        
        safe_name = param.replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_').replace('%', 'pct')
        plt.savefig(f"{output_dir}/{safe_name}_sop_limits.png")
        plt.close()

    print(f"\nParameter plots with SOP limits saved to '{output_dir}'.")

if __name__ == "__main__":
    visualize_bell_curves_with_limits('df_clustered_batches.xlsx')
