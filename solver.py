import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

min_driver_exp = {
    'A+': 10,
    'A': 3,
    'B': 0,
    'C': 0
}

def run_deadkm_optimization(driver_data, pickup_data, distance_matrix):
    driver_df = pd.DataFrame(driver_data)
    pickup_df = pd.DataFrame(pickup_data)
    distance_df = pd.DataFrame(distance_matrix)

    optimized_df, insights, chains = optimize_routes(driver_df, pickup_df, distance_df)

    return {
        'assignments': optimized_df,
        'insights': insights,
        'swap_chains': chains
    }

def optimize_routes(driver_df, pickup_df, distance_mat):
    dist = distance_mat.copy()
    for d in dist.index:
        driver = driver_df.loc[d]
        for p in dist.columns:
            pickup = pickup_df.loc[p]
            if driver['is_depot']:
                if pickup['cname'] not in driver['allowed_institutes']:
                    dist.at[d, p] = np.inf
            if driver['dexp'] < min_driver_exp[pickup['category']]:
                dist.at[d, p] = np.inf

    optim_drivers, optim_pickups = linear_sum_assignment(dist.to_numpy())
    result_df = pd.DataFrame({
        'From Bus': dist.index[optim_drivers],
        'To Bus': dist.columns[optim_pickups]
    })
    result_df['Dead KM'] = [dist.iat[i, j] for i, j in zip(optim_drivers, optim_pickups)]

    insights = {
        'total_dead_km': result_df['Dead KM'].sum(),
        'total_swaps': len(result_df),
    }

    chains = find_changed_chains(result_df['From Bus'].tolist(), result_df['To Bus'].tolist())
    return result_df, insights, chains

def find_changed_chains(from_buses, to_buses):
    visited = set()
    chains = []
    for i, start in enumerate(from_buses):
        if start in visited:
            continue
        chain = [start]
        current = to_buses[i]
        while current not in visited and current in from_buses:
            chain.append(current)
            visited.add(current)
            idx = from_buses.index(current)
            current = to_buses[idx]
        if len(chain) > 2:
            chains.append(chain)
    print(chains)
    return chains