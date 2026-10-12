import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np

def visualize_threshold(input_file, output_dir='visualizations_bell'):
    print(f"Reading clustered data from {input_file}...")
    df = pd.read_excel(input_file)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # The 'Cluster_Distance' is the metric used for the cut-off
    param = 'Cluster_Distance'
    
    plt.figure(figsize=(12, 7))
    
    # Plot KDE (Bell Curve) for the distance metric
    sns.kdeplot(data=df, x=param, fill=True, color='blue', label='Batch Signatures', alpha=0.3)
    
    # Find the threshold (95th percentile)
    threshold = df[param].quantile(0.95)
    
    # Add a vertical line for the cut-off
    plt.axvline(threshold, color='red', linestyle='--', linewidth=2, label=f'Cut-off Threshold ({threshold:.2f})')
    
    # Shade the Abnormal region
    x_kde, y_kde = sns.kdeplot(data=df, x=param).get_lines()[0].get_data()
    plt.fill_between(x_kde, y_kde, where=(x_kde > threshold), color='red', alpha=0.3, label='Abnormal Region (Top 5%)')
    
    # Stats for labeling
    text_str = (
        f"STATISTICAL CUT-OFF:\n"
        f"Threshold: {threshold:.2f}\n"
        f"Normal Batches: {len(df[df[param] <= threshold])}\n"
        f"Abnormal Batches: {len(df[df[param] > threshold])}"
    )
    
    plt.text(0.95, 0.70, text_str, transform=plt.gca().transAxes, fontsize=12,
             verticalalignment='top', horizontalalignment='right', 
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.title('How "Abnormal" is Defined: Distribution of Cluster Distances', fontsize=14)
    plt.xlabel('Distance from Standard Operating Procedure (SOP)', fontsize=12)
    plt.ylabel('Density', fontsize=12)
    plt.legend()
    plt.grid(True, alpha=0.2)
    
    plt.savefig(f"{output_dir}/Abnormality_Threshold_Logic.png")
    plt.close()

    print(f"\nThreshold logic plot saved to '{output_dir}/Abnormality_Threshold_Logic.png'.")

if __name__ == "__main__":
    visualize_threshold('df_clustered_batches.xlsx')
