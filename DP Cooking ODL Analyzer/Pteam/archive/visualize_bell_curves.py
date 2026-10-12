import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np

def visualize_bell_curves(input_file, output_dir='visualizations_bell'):
    print(f"Reading clustered data from {input_file}...")
    df = pd.read_excel(input_file)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # Get top 5 most important parameters based on previous analysis
    important_params = [
        'Deknotting Feed Flow (m3/h)_mean',
        'Screening Accept flow (m3/h)_mean',
        'Production ODL (ADT/D)_mean',
        'O2 to Mixer1_Oxygen feed at Reactor 1 (kg/h)_mean',
        'Press 1 Feed Cons (%)_mean'
    ]
    
    print(f"Generating bell curves for top parameters...")
    
    for param in important_params:
        plt.figure(figsize=(12, 7))
        
        # Plot KDE (Bell Curve) for Normal and Abnormal
        sns.kdeplot(data=df[df['Status_Flag'] == 'Normal'], x=param, fill=True, color='green', label='Normal (SOP)', alpha=0.4)
        sns.kdeplot(data=df[df['Status_Flag'] == 'Abnormal'], x=param, fill=True, color='red', label='Abnormal', alpha=0.4)
        
        # Calculate stats for labels
        stats = df.groupby('Status_Flag')[param].agg(['mean', 'std'])
        
        # Add text labels for stats
        text_str = (
            f"NORMAL:\nMean: {stats.loc['Normal', 'mean']:.2f}\nStd: {stats.loc['Normal', 'std']:.2f}\n\n"
            f"ABNORMAL:\nMean: {stats.loc['Abnormal', 'mean']:.2f}\nStd: {stats.loc['Abnormal', 'std']:.2f}"
        )
        
        # Position text box
        plt.text(0.95, 0.95, text_str, transform=plt.gca().transAxes, fontsize=12,
                 verticalalignment='top', horizontalalignment='right', 
                 bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        plt.title(f'Distribution Comparison: {param}', fontsize=14)
        plt.xlabel(param, fontsize=12)
        plt.ylabel('Density', fontsize=12)
        plt.legend()
        plt.grid(True, alpha=0.2)
        
        # Clean filename
        safe_name = param.replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_').replace('%', 'pct')
        plt.savefig(f"{output_dir}/{safe_name}_bell.png")
        plt.close()

    print(f"\nBell curve plots saved to the '{output_dir}' folder.")

if __name__ == "__main__":
    visualize_bell_curves('df_clustered_batches.xlsx')
