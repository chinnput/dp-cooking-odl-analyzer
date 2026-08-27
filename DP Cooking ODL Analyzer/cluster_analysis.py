import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt

def perform_clustering(input_file, output_file):
    print(f"Reading signatures from {input_file}...")
    df = pd.read_excel(input_file)
    
    # Identify feature columns (everything after metadata)
    metadata_cols = ['Digester_ID', 'Start_Time', 'End_Time', 'Row_Count', 'Duration_Min']
    features = [col for col in df.columns if col not in metadata_cols]
    
    # Drop rows with too many NaNs in features (if any)
    # Filling remaining NaNs with column means for clustering stability
    X = df[features].copy()
    X = X.fillna(X.mean())
    
    # 1. Scale the data
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # 2. Dimensionality Reduction (PCA) for visualization and better clustering
    pca = PCA(n_components=0.95) # Keep 95% of variance
    X_pca = pca.fit_transform(X_scaled)
    print(f"PCA reduced features from {len(features)} to {X_pca.shape[1]} components.")
    
    # 3. Clustering (K-Means)
    # Using 4 clusters as a starting point (might represent different operating modes or digesters)
    n_clusters = 4
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df['Cluster'] = kmeans.fit_transform(X_pca).argmin(axis=1) # Get cluster labels
    
    # 4. Calculate Distance to Cluster Center (to find "Abnormal" batches)
    # Outliers are batches far from their assigned cluster center
    distances = kmeans.transform(X_pca)
    df['Cluster_Distance'] = distances.min(axis=1)
    
    # Mark top 5% as "Abnormal" (potential outliers)
    threshold = df['Cluster_Distance'].quantile(0.95)
    df['Status_Flag'] = np.where(df['Cluster_Distance'] > threshold, 'Abnormal', 'Normal')
    
    # 5. Analysis of Clusters
    cluster_summary = df.groupby('Cluster').agg({
        'Digester_ID': 'count',
        'Cluster_Distance': 'mean',
        'Post O2 Kappa_Kappa online (%)_mean': 'mean'
    }).rename(columns={'Digester_ID': 'Batch_Count'})
    
    print("\nCluster Summary:")
    print(cluster_summary)
    
    print(f"\nIdentified {len(df[df['Status_Flag'] == 'Abnormal'])} abnormal batches.")
    
    print(f"Saving results to {output_file}...")
    df.to_excel(output_file, index=False)
    print("Done.")

if __name__ == "__main__":
    perform_clustering('df_batch_signatures.xlsx', 'df_clustered_batches.xlsx')
