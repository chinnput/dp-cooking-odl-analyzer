import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np

def visualize_all_bell_curves_with_limits(input_file, output_dir='visualizations_bell'):
    print(f"Reading clustered data from {input_file}...")
    df = pd.read_excel(input_file)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # Automatically identify ALL mean parameters (exclude metadata and status)
    # We look for all columns ending in '_mean'
    all_params = [col for col in df.columns if col.endswith('_mean')]
    
    print(f"Generating bell curves with SOP limits for {len(all_params)} parameters...")
    
    for param in all_params:
        try:
            plt.figure(figsize=(12, 7))
            
            # Filter out NaNs for KDE plotting
            normal_data = df[df['Status_Flag'] == 'Normal'][param].dropna()
            abnormal_data = df[df['Status_Flag'] == 'Abnormal'][param].dropna()
            
            if len(normal_data) < 2 or len(abnormal_data) < 2:
                print(f"Skipping {param} due to insufficient data points.")
                plt.close()
                continue

            # Plot KDE
            sns.kdeplot(data=normal_data, fill=True, color='green', label='Normal (SOP)', alpha=0.4)
            sns.kdeplot(data=abnormal_data, fill=True, color='red', label='Abnormal', alpha=0.4)
            
            # Calculate SOP Limits based on the Normal group (5th and 95th percentile)
            lower_limit = normal_data.quantile(0.05)
            upper_limit = normal_data.quantile(0.95)
            
            # Add vertical lines for SOP Limits
            plt.axvline(lower_limit, color='darkgreen', linestyle='--', linewidth=2, label=f'SOP Lower Limit ({lower_limit:.2f})')
            plt.axvline(upper_limit, color='darkgreen', linestyle='--', linewidth=2, label=f'SOP Upper Limit ({upper_limit:.2f})')
            
            plt.title(f'SOP Limits & Process Variation: {param}', fontsize=14)
            
            # Stats box
            text_str = (
                f"SOP WINDOW (Normal):\n"
                f"Low: {lower_limit:.2f} | High: {upper_limit:.2f}\n\n"
                f"ABNORMAL STATS:\n"
                f"Mean: {abnormal_data.mean():.2f}\n"
                f"Std: {abnormal_data.std():.2f}"
            )
            
            plt.text(0.05, 0.95, text_str, transform=plt.gca().transAxes, fontsize=11,
                     verticalalignment='top', horizontalalignment='left', 
                     bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            plt.xlabel(param, fontsize=12)
            plt.ylabel('Density', fontsize=12)
            plt.legend(loc='upper right')
            plt.grid(True, alpha=0.2)
            
            # Clean filename
            safe_name = param.replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_').replace('%', 'pct').replace(':', '')
            plt.savefig(f"{output_dir}/{safe_name}_sop_limits.png")
            plt.close()
        except Exception as e:
            print(f"Error plotting {param}: {e}")
            plt.close()

    print(f"\nAll {len(all_params)} parameter plots with SOP limits saved to '{output_dir}'.")

if __name__ == "__main__":
    visualize_all_bell_curves_with_limits('df_clustered_batches.xlsx')
