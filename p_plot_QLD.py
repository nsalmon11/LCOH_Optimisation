"""Plots QLD and puts relevant points onto the map"""

import pandas as pd
import matplotlib.pyplot as plt
from shapely.geometry import Point
import numpy as np
import seaborn as sns
import geopandas as gpd


def plot_map():
    """Plots map of QLD including transmission lines"""

    # Get map data
    raw_country_map = gpd.read_file(r'AusMap')
    raw_wire_data = gpd.read_file(r'ElectricityTransmissionLines_v2.gdb', layer='ElectricityTransmissionLines_v2')

    # Import site information:
    sites = pd.read_csv(r'Data/ProposedSites.csv')
    geometry = []
    for _, row in sites.iterrows():
        geometry.append(Point(row.Longitude, row.Latitude))
    sites['geometry'] = geometry
    sites = gpd.GeoDataFrame(sites, geometry='geometry')

    # Plot the figure
    custom_palette = sns.color_palette("Paired", 9)
    sns.set_theme(palette=custom_palette)
    sns.set_style(style='white')

    fig, ax = plt.subplots(figsize=(13, 13))
    ax.set_aspect('equal')
    raw_country_map.plot(ax=ax, color='white', edgecolor='black')
    raw_country_map.drop(2).plot(ax=ax, color='grey', edgecolor='black')
    raw_wire_data.plot(ax=ax, linewidth=0.5, label='Grid network')
    ax.set_xlim([135, 165])
    ax.set_ylim([-30, -5])

    sites.loc[sites['Dominant Renewable'] == 'Wind'].plot(markersize=5*(25 - sites['LCOH 2030']),
                                                          ax=ax,
                                                          label='Wind Production Sites',
                                                          color=custom_palette[1])
    sites.loc[sites['Dominant Renewable'] == 'Hybrid'].plot(markersize=5*(25 - sites['LCOH 2030']),
                                                            ax=ax,
                                                            label='Hybrid Production Sites',
                                                            color=custom_palette[2])
    sites.loc[sites['Dominant Renewable'] == 'Solar'].plot(markersize=5*(25 - sites['LCOH 2030']),
                                                           ax=ax,
                                                           label='Solar Production Sites',
                                                           color=custom_palette[4])

    for _, row in sites.iterrows():
        loc = row['geometry'].coords[0]
        if row.Location in ['SWQ', 'Western Downs']:
            x_adj = 0
            y_adj = -0.75
        else:
            x_adj = -2.5
            y_adj = 0.5
        ax.annotate(text='{a} ({b})'.format(a=row['Location'], b=row['Dominant Renewable']),
                    xy=(loc[0]+x_adj, loc[1]+y_adj), ha='center', fontsize=8)
        y_adj -= 0.5
        ax.annotate(text='2050 LCOH: {a} AUD/kg'.format(a=row['LCOH 2050']), xy=(loc[0]+x_adj, loc[1]+y_adj),
                    ha='center', fontsize=8)
        y_adj -= 0.5
        ax.annotate(text='2050 Prod. only: {a} AUD/kg'.format(a=row['LCOH 2050 No Store']), xy=(loc[0]+x_adj+0.3, loc[1]+y_adj),
                    ha='center', fontsize=8)

    ax.legend()
    plt.savefig('Storage comparison.png', bbox_inches='tight', format='png', dpi=500)

def plot_bar_results():
    """Plots the results on a bar chart"""

    sites = pd.read_csv('ProposedSites.csv').set_index('Location').sort_values(by='Dominant Renewable', ascending=False)
    x_nums = np.arange(len(sites.index))

    # Plot the figure
    custom_palette = sns.color_palette("Paired", 9)
    sns.set_theme(palette=custom_palette)
    sns.set_style(style='white')
    fig, ax = plt.subplots(figsize=(8, 8))

    ax.bar(x_nums-0.25, sites['LCOH 2030'], width=0.25, label='2030')
    ax.bar(x_nums, sites['LCOH 2050'], width=0.25, label='2050')
    ax.bar(x_nums+0.25, sites['LCOH 2050 No Store'], width=0.25, label='2050 no storage')
    ax.legend()

    x_labels = []
    for element in sites.index:
        x_labels.append('{a}\n({b})'.format(a=element.replace(" ", "\n"), b=sites.loc[element, 'Dominant Renewable']))
    plt.xticks(x_nums, x_labels)

    ax.set_ylabel('LCOH (AUD/kg)')
    plt.savefig('Cost_bars', bbox_inches='tight', format='png', dpi=500)

if __name__ == '__main__':
    plot_bar_results()