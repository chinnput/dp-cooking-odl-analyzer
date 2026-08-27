import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import numpy as np

def visualize_digester_performance(input_file, output_dir='visualizations_digester'):
    print(f"Reading clustered data from {input_file}...")
    df = pd.read_excel(input_file)
    
    # Ensure output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")
        
    # Standardize Digester ID as integer/string for categorical plotting
    df['Digester_ID'] = df['Digester_ID'].astype(int)
    
    # Identify all base parameters (matching parameter_mean and parameter_std)
    mean_cols = [col for col in df.columns if col.endswith('_mean')]
    
    # Determine unique base parameters
    base_params = [col[:-5] for col in mean_cols]
    
    print(f"Found {len(base_params)} parameters to analyze.")
    
    # Color palette for Digesters 1-4
    palette = {
        1: '#1f77b4', 2: '#ff7f0e', 3: '#2ca02c', 4: '#d62728',
        '1': '#1f77b4', '2': '#ff7f0e', '3': '#2ca02c', '4': '#d62728'
    }
    
    for param in base_params:
        mean_col = f"{param}_mean"
        std_col = f"{param}_std"
        
        # Check if both mean and std columns exist in dataframe
        if mean_col not in df.columns or std_col not in df.columns:
            print(f"Skipping {param}: Missing mean or std column.")
            continue
            
        # Filter out NaN values for this parameter to prevent plotting errors
        valid_data = df[df[mean_col].notnull() & df[std_col].notnull()].copy()
        
        if len(valid_data) == 0:
            print(f"Skipping {param}: No valid data points.")
            continue
            
        fig, axes = plt.subplots(1, 2, figsize=(16, 8))
        fig.suptitle(f'Digester Performance Analysis: {param}', fontsize=16, fontweight='bold', y=0.98)
        
        # Define mean marker properties for boxplot
        meanprops = {
            "marker": "D", 
            "markerfacecolor": "white", 
            "markeredgecolor": "black", 
            "markersize": 10,
            "label": "Overall Mean"
        }
        
        # ----------------- SUBPLOT 1: BATCH MEANS -----------------
        ax1 = axes[0]
        # Box plot of batch means by Digester
        sns.boxplot(
            x='Digester_ID', 
            y=mean_col, 
            data=valid_data, 
            ax=ax1, 
            palette=palette, 
            hue='Digester_ID',
            legend=False,
            showmeans=True, 
            meanprops=meanprops,
            width=0.5,
            fliersize=0 # Hide fliers as we show all batches with stripplot
        )
        # Overlay actual batch data points (stripplot)
        sns.stripplot(
            x='Digester_ID', 
            y=mean_col, 
            data=valid_data, 
            ax=ax1, 
            color='black', 
            alpha=0.25, 
            jitter=0.2, 
            size=4
        )
        
        ax1.set_title('Batch Average Values (Process Level)', fontsize=13, fontweight='bold')
        ax1.set_xlabel('Digester ID', fontsize=11)
        ax1.set_ylabel(f'Batch Mean ({param})', fontsize=11)
        ax1.grid(True, linestyle='--', alpha=0.5)
        
        # Calculate statistics for each digester and annotate subplot 1
        y_min, y_max = ax1.get_ylim()
        y_range = y_max - y_min
        
        for d_id in sorted(valid_data['Digester_ID'].unique()):
            d_data = valid_data[valid_data['Digester_ID'] == d_id][mean_col]
            if len(d_data) > 0:
                d_mean = d_data.mean()
                d_std = d_data.std()
                d_count = len(d_data)
                
                # Placement of text right above the box plot or at the top
                text_y = y_max - (y_range * 0.05)
                # Align text above each x-coordinate (0, 1, 2, 3)
                x_pos = d_id - 1
                
                stats_text = f"Mean: {d_mean:.2f}\nSD: {d_std:.2f}\nN: {d_count}"
                ax1.text(
                    x_pos, 
                    text_y, 
                    stats_text, 
                    ha='center', 
                    va='top', 
                    fontsize=9, 
                    fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7, edgecolor='gray')
                )
                
        # ----------------- SUBPLOT 2: WITHIN-BATCH STD DEVIATIONS -----------------
        ax2 = axes[1]
        # Box plot of batch std deviations (instability within batch) by Digester
        sns.boxplot(
            x='Digester_ID', 
            y=std_col, 
            data=valid_data, 
            ax=ax2, 
            palette=palette, 
            hue='Digester_ID',
            legend=False,
            showmeans=True, 
            meanprops=meanprops,
            width=0.5,
            fliersize=0
        )
        # Overlay actual batch data points (stripplot)
        sns.stripplot(
            x='Digester_ID', 
            y=std_col, 
            data=valid_data, 
            ax=ax2, 
            color='black', 
            alpha=0.25, 
            jitter=0.2, 
            size=4
        )
        
        ax2.set_title('Within-Batch Standard Deviations (Process Instability)', fontsize=13, fontweight='bold')
        ax2.set_xlabel('Digester ID', fontsize=11)
        ax2.set_ylabel(f'Batch Std Dev ({param})', fontsize=11)
        ax2.grid(True, linestyle='--', alpha=0.5)
        
        # Calculate statistics for each digester and annotate subplot 2
        y_min2, y_max2 = ax2.get_ylim()
        y_range2 = y_max2 - y_min2
        
        for d_id in sorted(valid_data['Digester_ID'].unique()):
            d_data = valid_data[valid_data['Digester_ID'] == d_id][std_col]
            if len(d_data) > 0:
                d_mean = d_data.mean()
                d_std = d_data.std()
                
                text_y = y_max2 - (y_range2 * 0.05)
                x_pos = d_id - 1
                
                stats_text = f"Mean SD: {d_mean:.2f}\nSD of SD: {d_std:.2f}"
                ax2.text(
                    x_pos, 
                    text_y, 
                    stats_text, 
                    ha='center', 
                    va='top', 
                    fontsize=9, 
                    fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7, edgecolor='gray')
                )
                
        plt.tight_layout()
        
        # Create safe filename
        safe_param_name = param.replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_').replace('%', 'pct')
        output_file_path = os.path.join(output_dir, f"{safe_param_name}_digester_performance.png")
        
        plt.savefig(output_file_path, dpi=150)
        plt.close()
        print(f"Generated plot: {output_file_path}")

    # Generate a tabular summary of statistics
    print("\nGenerating statistical excel summary...")
    summary_data = []
    for param in base_params:
        mean_col = f"{param}_mean"
        std_col = f"{param}_std"
        
        if mean_col in df.columns and std_col in df.columns:
            for d_id in sorted(df['Digester_ID'].unique()):
                d_df = df[df['Digester_ID'] == d_id]
                
                valid_means = d_df[mean_col].dropna()
                valid_stds = d_df[std_col].dropna()
                
                if len(valid_means) > 0:
                    summary_data.append({
                        'Parameter': param,
                        'Digester_ID': f"D{int(d_id)}",
                        'Batch_Count': len(valid_means),
                        'Batch_Mean_Avg': valid_means.mean(),
                        'Batch_Mean_Std': valid_means.std(),
                        'Batch_Mean_Min': valid_means.min(),
                        'Batch_Mean_Max': valid_means.max(),
                        'Within_Batch_Std_Avg': valid_stds.mean(),
                        'Within_Batch_Std_Std': valid_stds.std()
                    })
                    
    df_summary = pd.DataFrame(summary_data)
    summary_excel_path = 'digester_batch_performance_summary.xlsx'
    df_summary.to_excel(summary_excel_path, index=False)
    print(f"Excel summary saved to: {summary_excel_path}")
    print("All visualizations and summaries completed successfully!")

if __name__ == "__main__":
    visualize_digester_performance('df_clustered_batches.xlsx')
