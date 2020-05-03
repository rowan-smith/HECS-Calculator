import datetime

from flask import render_template, Blueprint
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from forms import HecsDebtForm

blueprint_name = "hecs_calculator"

hecs_calculator = Blueprint(blueprint_name, __name__)


@hecs_calculator.route(f'/{blueprint_name}', methods=['GET', 'POST'])
def _hecs_calculator():
    form = HecsDebtForm()
    display_strings = []
    display_blank_output = False

    if form.validate_on_submit():
        print("1 - Start Calculation Process")
        # Clear display strings and set index rate
        display_strings = []
        index_rate = 0.021

        # Set variables based on form data input
        annual_income = form.annual_income.data
        form.annual_income.data = ""
        hecs_debt = form.hecs_debt.data
        annual_voluntary_payment = form.weekly_voluntary_repayments.data * 52

        # Amount of money added onto the debt due to indexation
        annual_mandatory_hecs_repayment = get_annual_compulsory_hecs(annual_income)

        # Calculate num of years with voluntary repayments and resulting HECS debt
        num_voluntary_years, total_voluntary_index = get_num_voluntary_years(hecs_debt, index_rate,
                                                                             annual_voluntary_payment,
                                                                             annual_mandatory_hecs_repayment)
        voluntary_indexed_hecs = total_voluntary_index + hecs_debt

        # Calculate num of years without voluntary repayments and resulting HECS debt
        num_involuntary_years, total_involuntary_index = get_num_involuntary_years(hecs_debt, index_rate,
                                                                                   annual_mandatory_hecs_repayment)
        involuntary_indexed_hecs = total_involuntary_index + hecs_debt

        # Calculate num of years and months to repay debt for voluntary and involuntary payment
        voluntary_years, voluntary_months, involuntary_years, involuntary_months \
            = get_readable_repayment_lengths(num_involuntary_years, num_voluntary_years)

        # Append all strings that need to be displayed to the user to a list
        display_strings.append(f"${annual_income:,}")
        display_strings.append(f"${annual_voluntary_payment / 52:,.0f}")
        display_strings.append(f"${hecs_debt:,}")
        display_strings.append(f"{index_rate * 100}%")

        display_strings.append(f"{voluntary_years} years {voluntary_months} months "
                               f"(${voluntary_indexed_hecs:,.2f} indexed debt)")

        display_strings.append(f"{involuntary_years} years {involuntary_months} months "
                               f"(${involuntary_indexed_hecs:,.2f} indexed debt)")

        display_strings.append(f"{num_involuntary_years / num_voluntary_years:.2f}x quicker")
        display_strings.append(f"${involuntary_indexed_hecs - voluntary_indexed_hecs:,.2f} cheaper")
        display_strings.append(f"${annual_voluntary_payment / 52} weekly payments")
        display_strings.append(f"(${annual_voluntary_payment:,.2f} Annually)")

        display_blank_output = True
    return render_template(f"{blueprint_name}.html", form=form, display_strings=display_strings,
                           display_output=display_blank_output)


def get_annual_compulsory_hecs(annual_income):
    print("2 - Get Web Data")
    options = Options()

    options.headless = True
    # Executed as a script, the driver should be in `PATH` (root of directory)
    web_driver = webdriver.Chrome(options=options)

    # Go to Pay calculator page permalink for entered income
    current_time = datetime.datetime.now()
    # Permalink format: AnnualIncome|AnnualCycle|FinancialYear|SuperRate|DEFAULT_VALUES|Tick Hecs box
    web_driver.get(f"https://www.paycalculator.com.au/#{annual_income}|0|{current_time.year}|9.5|5,0,7.5,38,52|000100")

    # Get minimum hecs repayment, replace useless characters, convert to integer
    mandatory_hecs = web_driver.find_element_by_xpath("//*[@id='other_annually']").text
    chars_to_replace = ["$", ","]
    for char in chars_to_replace:
        mandatory_hecs = mandatory_hecs.replace(char, "")
    mandatory_hecs = float(mandatory_hecs)
    web_driver.close()
    return mandatory_hecs


def get_num_voluntary_years(hecs_debt, index_rate, annual_voluntary_payment, mandatory_hecs_repayment):
    print("3 - Calculate voluntary years")
    calculated_num_years = 1
    annual_index_amounts = []

    # Assign hecs to variable that will be manipulated
    initial_hecs = hecs_debt

    # Set the index amount to index rate of first indexation period
    index_amount = initial_hecs * index_rate
    annual_index_amounts.append(index_amount)

    # calculate indexed hecs debt after 1 year (While loop uses this recursively to give correct index amount each year)
    voluntary_indexed_amount = index_amount + hecs_debt - (
            (annual_voluntary_payment + mandatory_hecs_repayment) * calculated_num_years)

    while voluntary_indexed_amount > 0:
        index_amount = voluntary_indexed_amount * index_rate
        voluntary_indexed_amount = index_amount * calculated_num_years + hecs_debt - (
                (annual_voluntary_payment + mandatory_hecs_repayment) * calculated_num_years)
        if calculated_num_years % 1 <= 0.1:
            annual_index_amounts.append(index_amount)
        calculated_num_years += 0.1
    return calculated_num_years, sum(annual_index_amounts)


def get_num_involuntary_years(hecs_debt, index_rate, mandatory_hecs_repayment):
    print("4 - Calculate involuntary years")
    calculated_num_years = 1
    annual_index_amounts = []

    # Assign hecs to variable that will be manipulated
    initial_hecs = hecs_debt

    # Set the index amount to index rate of first indexation period
    index_amount = initial_hecs * index_rate
    annual_index_amounts.append(index_amount)

    # calculate indexed hecs debt after 1 year (While loop uses this recursively to give correct index amount each year)
    involuntary_indexed_amount = index_amount + hecs_debt - (mandatory_hecs_repayment * calculated_num_years)

    while involuntary_indexed_amount > 0:
        involuntary_indexed_amount = index_amount + hecs_debt - (
                mandatory_hecs_repayment * calculated_num_years)
        if calculated_num_years % 1 <= 0.1:
            annual_index_amounts.append(index_amount)
        calculated_num_years += 0.1
    return calculated_num_years, sum(annual_index_amounts)


def get_readable_repayment_lengths(num_involuntary_years, num_voluntary_years):
    print("5 - Convert calculated dates to readable format")
    voluntary_years = int(num_voluntary_years)
    voluntary_months = int((num_voluntary_years % 1) * 12)
    involuntary_years = int(num_involuntary_years)
    involuntary_months = int((num_involuntary_years % 1) * 12)
    return voluntary_years, voluntary_months, involuntary_years, involuntary_months
