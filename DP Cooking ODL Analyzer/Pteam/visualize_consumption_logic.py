import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os

def generate_consumption_logic_plot(input_file, output_img='Specific_Consumption_Logic_Explanatory.png'):
    print(f"Reading clustered data from {input_file}...")
    df = pd.read_excel(input_file)
    
    # Clean data
    df['Digester_ID'] = df['Digester_ID'].astype(int)
    df['Status_Flag'] = df['Status_Flag'].astype(str)
    
    prod_col = 'Production ODL (ADT/D)_mean'
    steam_col = 'Specific Steam Consumption (t_ADT)_mean'
    steam_flow_col = 'MP Steam Pulp Heat_Feed before Reactor 2 (t/h)_mean'
    
    if prod_col not in df.columns or steam_col not in df.columns or steam_flow_col not in df.columns:
        print("Error: Required columns for explanation plot not found.")
        return
        
    # Drop NaNs
    valid_df = df[df[prod_col].notnull() & df[steam_col].notnull() & df[steam_flow_col].notnull()].copy()
    
    # Separate Normal and Abnormal
    normal_df = valid_df[valid_df['Status_Flag'] == 'Normal']
    abnormal_df = valid_df[valid_df['Status_Flag'] == 'Abnormal']
    
    avg_normal_steam_flow = normal_df[steam_flow_col].mean()
    print(f"Average Normal Steam Flow: {avg_normal_steam_flow:.4f} t/h")
    
    # Create the figure
    plt.figure(figsize=(12, 8))
    
    # 1. Plot the actual batch data points
    palette = {'Normal': '#2ca02c', 'Abnormal': '#d62728'}
    sns.scatterplot(
        x=prod_col,
        y=steam_col,
        hue='Status_Flag',
        data=valid_df,
        palette=palette,
        alpha=0.6,
        s=50,
        edgecolor='black',
        linewidth=0.5
    )
    
    # 2. Draw the theoretical Specific Consumption curve (y = 24 * Flow / Production)
    # Generate points for production rate
    x_curve = np.linspace(5, 350, 500)
    # We use the average normal steam flow as the reference
    y_curve = 24.0 * avg_normal_steam_flow / x_curve
    
    plt.plot(
        x_curve, 
        y_curve, 
        color='blue', 
        linestyle='--', 
        linewidth=2.5, 
        label=f'Theoretical Consumption Curve (at constant flow of {avg_normal_steam_flow:.2f} t/h)'
    )
    
    # 3. Add Annotations to explain the areas
    # Normal Zone
    plt.axvspan(240, 310, color='lightgreen', alpha=0.15, label='Normal Production Zone')
    plt.annotate(
        'Normal Operating Zone\n• Production: 240–310 ADT/D\n• Specific Consumption: ~0.09 t/ADT\n• Stable & Highly Efficient',
        xy=(275, 0.2),
        xytext=(200, 2.5),
        arrowprops=dict(facecolor='green', shrink=0.05, width=1.5, headwidth=6, headlength=6),
        fontsize=10,
        fontweight='bold',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='green', alpha=0.9)
    )
    
    # Abnormal / Trip Zone
    plt.axvspan(0, 150, color='salmon', alpha=0.15, label='Process Slowdown / Trip Zone')
    plt.annotate(
        'Abnormal / Trip Zone\n• Production falls to <150 ADT/D\n• Steam flow remains active\n• Specific Consumption explodes!\n• Massive Energy & Chemical Waste',
        xy=(60, 4.0),
        xytext=(100, 5.5),
        arrowprops=dict(facecolor='red', shrink=0.05, width=1.5, headwidth=6, headlength=6),
        fontsize=10,
        fontweight='bold',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='red', alpha=0.9)
    )
    
    # Plot layout adjustments
    plt.title('The Mathematical Mechanism of Specific Consumption Spikes', fontsize=15, fontweight='bold')
    plt.xlabel('Production Rate (ADT/D)', fontsize=12, fontweight='bold')
    plt.ylabel('Specific Steam Consumption (t/ADT)', fontsize=12, fontweight='bold')
    
    # Cap the Y-axis so data is within 70% of the graph height
    # Max visible data point we care about is ~5.5, so 8.0 is perfect (5.5 / 8.0 = 68.75% height)
    plt.ylim(0, 8.0)
    plt.xlim(0, 350)
    plt.grid(True, linestyle='--', alpha=0.4)
    plt.legend(loc='upper right', fontsize=10)
    
    # Draw a line showing the 70% height cap boundary just for clear reference
    plt.axhline(5.6, color='gray', linestyle=':', alpha=0.3)
    plt.text(345, 5.7, '70% Height Threshold', color='gray', ha='right', fontsize=9, alpha=0.7)
    
    plt.tight_layout()
    plt.savefig(output_img, dpi=150)
    plt.close()
    print(f"Logic explanation plot successfully saved to {output_img}")

if __name__ == "__main__":
    generate_consumption_logic_plot('df_clustered_batches.xlsx')
