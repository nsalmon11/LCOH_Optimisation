import pypsa
import numpy as np
import pandas as pd
import logging


def create_override_components():
    """Set up new component attributes as required"""
    # Modify the capacity of a link so that it can attach to 2 buses.
    override_component_attrs = pypsa.descriptors.Dict(
        {k: v.copy() for k, v in pypsa.components.component_attrs.items()}
    )

    override_component_attrs["Link"].loc["bus2"] = [
        "string",
        np.nan,
        np.nan,
        "2nd bus",
        "Input (optional)",
    ]
    override_component_attrs["Link"].loc["efficiency2"] = [
        "static or series",
        "per unit",
        1.0,
        "2nd bus efficiency",
        "Input (optional)",
    ]
    override_component_attrs["Link"].loc["p2"] = [
        "series",
        "MW",
        0.0,
        "2nd bus output",
        "Output",
    ]
    return override_component_attrs


def get_col_widths(dataframe):
    # First we find the maximum length of the index column
    idx_max = max([len(str(s)) for s in dataframe.index.values] + [len(str(dataframe.index.name))])
    # Then, we concatenate this to the max of the lengths of column name and its values for each column, left to right
    return [idx_max] + [max([len(str(s)) for s in dataframe[col].values] + [len(col)]) for col in dataframe.columns]



def extra_functionalities(n, snapshots):
    """Might be needed if additional constraints are needed later"""
    pass


def get_weather_data(file_name=None):
    """Asks the user where the weather data is, and pulls it in. Keeps asking until it gets a file.
    If a file_name has already been provided this code just imports the data. """
    # import data
    if file_name is None:
        input_check = True
        while input_check:
            try:
                input_check = False
                file = input("What is the name of your weather data file? "
                             "It must be a CSV, but don't include the file extension >> ")
                weather_data = pd.read_csv(file + '.csv')
                weather_data.drop(weather_data.columns[0], axis=1, inplace=True)
            except FileNotFoundError:
                input_check = True
                print("There's no input file there! Try again.")

        # Check the weather data is a year long
        if len(weather_data) < 8700 or len(weather_data) > 8760 + 48:
            logging.warning('Your weather data seems not to be one year long in hourly intervals. \n'
                            'Are you sure the input data is correct?'
                            ' If not, exit the code using ctrl+c and start again.')

    else:
        weather_data = pd.read_csv(file_name + '.csv')
        weather_data.drop(weather_data.columns[0], axis=1, inplace=True)

    return weather_data

def check_CAPEX(file_name=None):
    """Checks if the user has put the CAPEX into annualised format. If not, it helps them do so.
    file_name is the wather data file - if it is not specified the user is asked.
    Otherwise this function does nothing."""
    if file_name is None:
        check = input('Are your capital costs in the generators.csv, '
                            'components.csv and stores.csv files annualised?'
                        '\n (i.e. have you converted them from their upfront capital cost'
                        ' to the cost that accrues each year under the chosen financial conditions? \n'
                        '(Y/N) >> ')
    else:
        check = 'Y'
    if check != 'Y':
        print('You have selected no annualisation, which means you have entered the upfront capital cost'
              ' of the equipment. \n We have to ask you a few questions to convert these to annualised costs.')
        check2 = True
        while check2:
            try:
                discount = float(input('Enter the weighted average cost of capital in percent (i.e. 7 not 0.07)'))
                years = float(input('Enter the plant operating years.'))
                O_and_M = float(input('Enter the fixed O & M costs as a percentage of installed CAPEX '
                                      '(i.e. 2 not 0.02)'))
                check2 = False
            except ValueError:
                logging.warning('You have to enter a number! Try again.')
                check2 = True

        crf = discount * (1 + discount) ** years / ((1 + discount) ** years - 1)
        if crf < 2 or crf > 20 or O_and_M < 0 or O_and_M > 8:
            print('Your financial parameter inputs are giving some strange results. \n'
                  'You might want to exit the code using ctrl + c and try re-entering them.')

        return crf, O_and_M
    else:
        if file_name is None:
            print('You have selected the annualised capital cost entry. \n'
                  'Make sure that the annualised capital cost data includes any operating costs that you '
                  'estimate based on plant CAPEX.')
        return None

def get_solving_info(file_name=None):
    """Prompts the user for information about the solver and the problem formulation.
    If no file_name is provided then the model will autoselect gurobi and pyomo."""
    if file_name is None:
        solver = input('What solver would you like to use? '
                       'If you leave this blank, the glpk default will be used >> ')
        if solver == '':
            solver = 'glpk'

        formulator = input("Would you like to formulate the problem using pyomo or linopt? \n"
                           "Linopt can be faster but it is less user friendly. \n"
                           "The answer only matters if you've added some extra constraints. (p/l) >> ")
    else:
        solver = 'gurobi'
        formulator = 'l'
    return solver, formulator

def get_scale(n, file_name=None):
    """Gives the user some information about the solution, and asks if they'd like it to be scaled.
    If the file_name is prespecified the scale is automatically 1 (i.e. no scaling)"""
    if file_name is None:
        print('\nThe unscaled generation capacities are:')
        print(n.generators.rename(columns={'p_nom_opt': 'Rated Capacity (MW)'})[['Rated Capacity (MW)']])
        print('The unscaled hydrogen production is {a} t/year\n'.format(a=n.loads.p_set.values[0]/39.4*8760))
        scale = input('Enter a scaling factor for the results, to adjust the production. \n'
                       "If you don't want to scale the results, enter a value of 1 >> ")
        try:
            scale = float(scale)
        except ValueError:
            scale = 1
            print("You didn't enter a number! The results won't be scaled.")
        return scale
    else:
        return 1

def get_results_dict_for_excel(n, scale):
    """Takes the results and puts them in a dictionary ready to be sent to Excel"""
    # Rename the components:
    links_name_dct = {'p_nom_opt': 'Rated Capacity (MW)',
                      'carrier': 'Carrier',
                      'bus0': 'Primary Energy Source',
                      'bus2': 'Secondary Energy Source'}
    comps = n.links.rename(columns=links_name_dct)[[i for i in links_name_dct.values()]]
    comps["Rated Capacity (MW)"] *= scale

    # Get the energy flows
    primary = n.links_t.p0*scale
    secondary = (n.links_t.p2*scale).drop(columns=['Hydrogen from storage', 'Electrolysis'])

    # Rescale the energy flows:
    primary['Hydrogen Compression'] /= 39.4
    primary['Hydrogen from storage'] /= 39.4

    # Rename the energy flows
    primary.rename(columns={
        'Electrolysis': 'Electrolysis (MW)',
        'Hydrogen Compression': 'Hydrogen to storage (t/h)',
        'Hydrogen from storage': 'Hydrogen from storage (t/h)'
    }, inplace=True)
    secondary.rename(columns={'Hydrogen Compression': 'H2 Compression Power Consumption (MW)'}, inplace=True)

    consumption = pd.merge(primary, secondary, left_index=True, right_index=True)

    output = {
        'Headlines': pd.DataFrame({
            'Objective function (USD/kg)': [n.objective/(n.loads.p_set.values[0]/39.4*8760*1000)],
            'Production (t/year)': n.loads.p_set.values[0]/39.4*8760*scale}, index=['LCOH (USD/kg)']),
        'Generators': n.generators.rename(columns={'p_nom_opt': 'Rated Capacity (MW)'})[['Rated Capacity (MW)']]*scale,
        'Components': comps,
        'Stores': n.stores.rename(columns={'e_nom_opt': 'Storage Capacity (MWh)'})[['Storage Capacity (MWh)']]*scale,
        'Energy generation (MW)': n.generators_t.p*scale,
        'Energy consumption': consumption,
        'Stored energy capacity (MWh)': n.stores_t.e*scale
    }
    return output


def write_results_to_excel(output, file_name=None, extension=None):
    """Takes results dictionary and puts them in an excel file. User determines the file name"""
    if file_name is None:
        incomplete = True
        while incomplete:
            output_file = input("Enter the name of your output data file. \n"
                                "Don't include the file extension. >> ") + '.xlsx'
            try:
                incomplete = False
                with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
                    for key in output.keys():
                        dataframe = output[key]
                        dataframe.to_excel(writer, sheet_name=key)
                        worksheet = writer.sheets[key]
                        for i, width in enumerate(get_col_widths(dataframe)):
                            worksheet.set_column(i, i, width)
            except PermissionError:
                incomplete = True
            print('There is a problem writing on that file. Try another excel file name.')
    else:
        output_file = file_name + extension + '.xlsx'
        with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
            for key in output.keys():
                dataframe = output[key]
                dataframe.to_excel(writer, sheet_name=key)
                worksheet = writer.sheets[key]
                for i, width in enumerate(get_col_widths(dataframe)):
                    worksheet.set_column(i, i, width)
