import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

min_driver_exp={
    'A+': 10,
    'A': 0,
    'B': 0,
    'C': 0
}

def run_deadkm_optimization(driver_data, pickup_data, distance_matrix):
    driver_df=pd.DataFrame(driver_data)
    pickup_df=pd.DataFrame(pickup_data)
    distance_df=pd.DataFrame(distance_matrix)

    optimized_df, insights, chains=optimize_routes(driver_df, pickup_df, distance_df)

    return {
        'assignments': optimized_df,
        'insights':insights,
        'swap_chains':chains
    }

def optimize_routes(driver_df, pickup_df, distance_mat):
    dist=distance_mat.copy()
    for d in dist.index:
        driver=driver_df.loc[d]
        for p in dist.columns:
            pickup=pickup_df.loc[p]
            if driver['is_depot']:
                if pickup['cname'] not in driver['allowed_institutes']:
                    dist.at[d, p]=np.inf
            if driver['dexp'] < min_driver_exp[pickup['category']]:
                dist.at[d, p]=np.inf

    optim_drivers, optim_pickups=linear_sum_assignment(dist.to_numpy())
    result_df=pd.DataFrame({
        'From Bus': dist.index[optim_drivers],
        'To Bus': dist.columns[optim_pickups]
    })
    result_df['Dead KM']=[dist.iat[i, j] for i, j in zip(optim_drivers, optim_pickups)]

    insights={
        'total_dead_km': result_df['Dead KM'].sum(),
        'total_swaps': len(result_df),
    }

    chains=find_changed_chains(result_df['From Bus'].tolist(), result_df['To Bus'].tolist())
    return result_df, insights, chains

def find_changed_chains(from_buses, to_buses):
    visited=set()
    chains=[]
    for i, start in enumerate(from_buses):
        if start in visited:
            continue
        chain=[start]
        current=to_buses[i]
        while current not in visited and current in from_buses:
            chain.append(current)
            visited.add(current)
            idx=from_buses.index(current)
            current=to_buses[idx]
        if len(chain) > 2:
            chains.append(chain)
    print(chains)
    return chains

def get_swap_details(chains, optimized_df, driver_df):
    output_rows=[]
    totals_summary=[]

    for i, chain in enumerate(chains, 1):
        vehicles=chain
        routes=[str(driver_df.loc[v, 'route']) if v in driver_df.index else 'NA' for v in vehicles]
        institutes=[str(driver_df.loc[v, 'cname']) if v in driver_df.index else 'NA' for v in vehicles]
        
        row_chain=[f'Chain {i}'] + [''] * (len(vehicles) - 1)
        row_vehicles=['Vehicles'] + vehicles
        row_routes=['Routes'] + routes
        row_institutes=['Institutes'] + institutes
        
        output_rows.extend([row_chain, row_vehicles, row_routes, row_institutes])
        
        mask=optimized_df['From Bus'].isin(vehicles)
        total_opt_dead_km=optimized_df.loc[mask, 'Optimized dead km'].sum()
        total_orig_dead_km=optimized_df.loc[mask, 'Original dead km'].sum()
        totals_summary.append([
            f'Chain {i}',
            len(vehicles),
            round(total_opt_dead_km, 2),
            round(total_orig_dead_km, 2)
        ])
    output_rows.append(['']*max(len(r) for r in output_rows))

    output_rows.append(['Swap Chain', 'Count', 'Optimized km', 'Original km'])
    output_rows.extend(totals_summary)
    output_df=pd.DataFrame(output_rows)
    return output_df