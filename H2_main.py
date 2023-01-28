import pypsa
import p_H2_aux as aux

"""
File to optimise the size of a green hydrogen plant given a specified wind and solar profile
User is prompted for all inputs
N Salmon 28/01/2023
"""


def main():
    """Code to execute run at a single location"""
    # ==================================================================================================================
    # Set up network
    # ==================================================================================================================

    # Import the weather data
    weather_data = aux.get_weather_data()

    # Import a generic network
    n = pypsa.Network(override_component_attrs=aux.create_override_components())

    # Set the time values for the network
    n.set_snapshots(range(len(weather_data)))

    # Import the design of the H2 plant into the network
    n.import_from_csv_folder("Basic_H2_plant")

    renewables_lst = n.generators.index.to_list()
    # Note: All flows are in MW or MWh, conversions for hydrogen done using HHVs. Hydrogen HHV = 39.4 MWh/t

    # ==================================================================================================================
    # Send the weather data to the model
    # ==================================================================================================================

    count = 0
    for name, dataframe in weather_data.items():
        if name in renewables_lst:
            n.generators_t.p_max_pu[name] = dataframe
            count += 1
        else:
            raise ValueError("You have weather data that isn't in your list of renewables, so I don't know what those "
                             " renewables cost. \n Edit generators.csv to include all of the renewables for which you've "
                             " provided data")
    if count != len(renewables_lst):
        raise ValueError("You have renewables for which you haven't provided a weather dataset. "
                         "\n Edit the input file to include all relevant renewables sources, "
                         "or remove the renewables sources from generators.csv")

    # ==================================================================================================================
    # Check if the CAPEX input format in Basic_H2_plant is correct, and fix it up if not
    # ==================================================================================================================

    CAPEX_check = aux.check_CAPEX()
    if CAPEX_check is not None:
        for item in [n.generators, n.links, n.stores]:
            item.capital_cost = item.capital_cost * CAPEX_check[1]/100 + item.capital_cost/CAPEX_check[0]

    # ==================================================================================================================
    # Solve the model
    # ==================================================================================================================

    # Ask the user how they would like to solve
    solver, formulator = aux.get_solving_info()

    # Implement their answer
    if formulator == 'l':
        print("You're not using pyomo!")
        n.lopf(solver_name=solver, pyomo=False, extra_functionality=aux.extra_functionalities)
    else:
        print("You're using pyomo!")
        n.lopf(solver_name=solver, pyomo=True)

    # ==================================================================================================================
    # Output results
    # ==================================================================================================================

    # Scale if needed
    scale = aux.get_scale(n)

    # Put the results in a nice format
    output = aux.get_results_dict_for_excel(n, scale)

    # Send the results to excel
    aux.write_results_to_excel(output)


if __name__ == '__main__':
    main()
