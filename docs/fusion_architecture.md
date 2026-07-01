# ClimateTwin AI: Data Architecture & Fusion Strategy

## Overview

Climate forecasting heavily depends on the spatial density and quality of historical data. The primary challenge in regional climate modeling is the sparse geographical coverage of physical ground stations. To solve this, **ClimateTwin AI** employs a multi-modal data architecture that fuses hyper-localized ground station observations with continuous, high-resolution satellite imagery.

This document details our ingestion pipeline, data fusion algorithm, and how it powers our deep learning predictive models.

## 1. The Challenge: Ground Station Sparsity

Traditional weather datasets rely entirely on ground stations (like those operated by the IMD - Indian Meteorological Department). While highly accurate, these stations are physically sparse, often leaving massive blind spots in rural areas, oceans, and mountains. 

If an AI model is trained purely on ground-station data, it fundamentally cannot predict accurate micro-climates for locations far away from a physical sensor.

## 2. The Solution: INSAT-3DR Satellite Fusion

To eliminate these blind spots, we integrated **INSAT-3DR HDF5 Satellite Data** (specifically Land Surface Temperature and INSAT Multispectral Rainfall estimations). Satellites provide a continuous grid of data across the entire country, regardless of terrain.

Our system successfully ingests and merges both of these massive datasets into a unified PostgreSQL database, creating a "Climate Twin" that has both the pinpoint accuracy of ground stations and the continuous coverage of satellite observations.

### Ingestion Pipeline Performance
Processing satellite HDF5 imagery at scale is computationally intensive. Our ingestion pipeline parses, clips to the regional bounding box, and inserts data into the database. 
To achieve maximum performance and avoid standard SQLAlchemy `INSERT` bottlenecks, we implemented a custom asynchronous `asyncpg` stream using the binary PostgreSQL `COPY` protocol. This allows us to ingest **~600,000 records per file at warp speed**, gracefully scaling to hundreds of millions of rows overnight.

## 3. Data Fusion Algorithm

Our data fusion layer (`data_fusion.py`) acts as the central nervous system of the application. Before any data reaches the AI model, it passes through this layer, which automatically applies one of three strategies:

1. **Weighted Fusion (Primary):** When both ground station and satellite data exist for a specific grid cell on a specific day, the system applies a weighted average. We trust the ground-truth physical sensors slightly more:
   `Fused Value = (0.6 * Ground_Station_Value) + (0.4 * Satellite_Value)`
2. **Satellite-Only (Failover):** For ocean coordinates or remote areas where no physical ground stations exist, the system automatically falls back to utilizing 100% satellite data, preventing data gaps.
3. **Ground-Only (Fallback):** For variables that lack satellite coverage (like Minimum Temperature), the system gracefully falls back to using the pure IMD ground data.

## 4. LSTM Predictive Modeling

With a fully realized, dense, and continuous historical dataset, we train a **Multi-layer LSTM (Long Short-Term Memory) Neural Network**. 

- **Architecture:** 2 hidden layers, 128 hidden units, 20% Dropout.
- **Sequence Length:** The model looks back at a 30-day historical window.
- **Forecast Horizon:** The model predicts the next 7 days simultaneously.
- **Input Features:** Fused Rainfall, Fused Max Temp, Fused Min Temp.

Because the LSTM model is trained on this enriched, fused dataset, its temporal predictions are significantly more robust against localized anomalies, giving ClimateTwin AI its predictive edge.
