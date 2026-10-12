import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

def visualize_results(input_file, output_dir='visualizations'):
    print(f"Reading clustered data from {input_file}...")
    df = pd.read_excel(input_file)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # Get all mean parameters (ending in _mean)
    mean_params = [col for col in df.columns if col.endswith('_mean') and 'Kappa' not in col]
    
    print(f"Generating comparison plots for {len(mean_params)} parameters...")
    
    # We will create one large multi-plot figure to keep it manageable, 
    # and also individual plots if needed.
    
    # For simplicity in this environment, let's create a summary PDF or a series of images.
    # Since I can't show a PDF easily, I'll describe the trend and save the plots.
    
    for param in mean_params:
        plt.figure(figsize=(10, 6))
        sns.boxplot(x='Status_Flag', y=param, data=df, palette={'Normal': 'lightgreen', 'Abnormal': 'salmon'})
        plt.title(f'Normal vs Abnormal: {param}')
        plt.grid(True, alpha=0.3)
        
        # Clean filename
        safe_name = param.replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_').replace('%', 'pct')
        plt.savefig(f"{output_dir}/{safe_name}.png")
        plt.close()

    # Create a summary table of the biggest differences
    summary_stats = df.groupby('Status_Flag')[mean_params].mean().T
    summary_stats['Difference_Pct'] = ((summary_stats['Abnormal'] - summary_stats['Normal']) / summary_stats['Normal']) * 100
    summary_stats = summary_stats.sort_values(by='Difference_Pct', key=abs, ascending=False)
    
    print("\nTop 10 Parameters showing the biggest difference between Normal and Abnormal:")
    print(summary_stats.head(10))
    
    summary_stats.to_excel(f"{output_dir}/parameter_differences.xlsx")
    print(f"\nAll plots saved to the '{output_dir}' folder.")

if __name__ == "__main__":
    visualize_results('df_clustered_batches.xlsx')
