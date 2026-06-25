import numpy as np

files = {
    "rainfall": r"D:\data\Rainfall_ind2025_rfp25.grd",
    "mintemp": r"D:\data\Mintemp_MinT_2025.GRD",
    "maxtemp": r"D:\data\Maxtemp_MaxT_2025.GRD",
}

for name, path in files.items():
    data = np.fromfile(path, dtype=np.float32)

    print("\n====================")
    print("Dataset:", name)
    print("Total values:", len(data))
    print("Min value:", data.min())
    print("Max value:", data.max())
    print("Sample (first 10):", data[:10])