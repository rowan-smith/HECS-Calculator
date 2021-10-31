from datetime import datetime

import gspread
import requests
from bs4 import BeautifulSoup
from flask import render_template, Blueprint
from markupsafe import Markup
from oauth2client.service_account import ServiceAccountCredentials

from forms import HecsDebtForm
from static.Helper_Classes.UserHecsCalculations import UserHecsTax

ATO_HELP_THRESHOLD_URL = "https://www.ato.gov.au/Rates/HELP,-TSL-and-SFSS-repayment-thresholds-and-rates/"
ATO_HELP_INDEXATION_URL = "https://www.ato.gov.au/Rates/Study-and-training-loan-indexation-rates/"

blueprint_name = "hecs_calculator"

# ====== GOOGLE SHEET CONNECTION DEFINED BELOW TO SPEED UP RESPONSE TIME TO THE USER ======
# use creds to create a client to interact with the Google Drive API
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']

# WEB VERSION
credentials = ServiceAccountCredentials.from_json_keyfile_name('Nick_Barty_Website/static/client_secret.json', scope)

# DEV VERSION
# credentials = ServiceAccountCredentials.from_json_keyfile_name('static/client_secret.json', scope)

client = gspread.authorize(credentials)

# Find a workbook by name and open the first sheet
sheet = client.open("Hecs Calculator Log").sheet1
# ====== GOOGLE SHEET CONNECTION DEFINED ABOVE TO SPEED UP RESPONSE TIME TO THE USER ======

hecs_calculator = Blueprint(blueprint_name, __name__)


@hecs_calculator.route(f'/{blueprint_name}', methods=['GET', 'POST'])
def _hecs_calculator():
    form = HecsDebtForm()
    display_strings = []
    error_strings = []
    g_sheet_new_row = []
    display_output = False

    if form.validate_on_submit():
        # Clear display strings
        # display_strings = []
        # error_strings = []

        income_threshold_brackets = get_values_from_ato_table(ATO_HELP_THRESHOLD_URL)
        yearly_indexation_rates = get_values_from_ato_table(ATO_HELP_INDEXATION_URL, 2)

        # Set variables based on form data input
        annual_income = form.annual_income.data
        hecs_debt = form.hecs_debt.data
        weekly_repayments = form.weekly_voluntary_repayments.data
        monthly_repayments = (weekly_repayments * 52) / 12

        user_hecs_tax = UserHecsTax(annual_income, income_threshold_brackets, yearly_indexation_rates)
        index_rate = user_hecs_tax.average_yearly_indexation_rate

        # Prepare google sheet entry data
        g_sheet_new_row = [annual_income, hecs_debt, weekly_repayments]
        time_split = str(datetime.astimezone(datetime.now())).split(".")
        date_time = time_split[0]
        timezone = f"'{time_split[1][6:]}"  # Format with apostrophe so no formula is applied in google sheets

        try:
            involuntary_values, total_of_indexed_values = calculate_hecs_repayments(hecs_debt,
                                                                                    user_hecs_tax.average_yearly_indexation_rate,
                                                                                    user_hecs_tax.user_income_hecs_tax_amount,
                                                                                    0, False)
            # Total indexed amount of debt
            total_involuntary_index = (sum(total_of_indexed_values))

            voluntary_values, total_of_indexed_values = calculate_hecs_repayments(hecs_debt,
                                                                                  user_hecs_tax.average_yearly_indexation_rate,
                                                                                  user_hecs_tax.user_income_hecs_tax_amount,
                                                                                  monthly_repayments,
                                                                                  True)

            total_voluntary_index = (sum(total_of_indexed_values))
            # Append all strings that need to be displayed to the user to a list
            # display_strings.append(f"Annual Income: <b>${annual_income:,}</b>")
            display_strings.append(Markup(f"${annual_income:,}"))
            display_strings.append(Markup(f"${hecs_debt:,}"))
            display_strings.append(
                Markup(
                    f"${user_hecs_tax.user_income_hecs_tax_amount:,} ({user_hecs_tax.user_tax_bracket_tax_rate}%)"))
            display_strings.append(Markup(f"${weekly_repayments:,.0f}"))
            display_strings.append(Markup(f"{round(index_rate * 100, 2)}%"))
            display_strings.append(Markup(
                f"Approximate voluntary repayment length:<br> <b>{int(len(voluntary_values) / 12)} years {len(voluntary_values) % 12} months</b> "
                f"<i>(${hecs_debt + total_voluntary_index :,.2f} total debt)</i>"))
            display_strings.append(Markup(
                f"Approximate involuntary repayment length:<br> <b>{int(len(involuntary_values) / 12)} years {len(involuntary_values) % 12} months</b> "
                f"<i>(${hecs_debt + total_involuntary_index:,.2f} total debt)</i>"))
            year_difference = int(len(involuntary_values) / 12) - int(len(voluntary_values) / 12)
            try:
                times_quicker = len(involuntary_values) / len(voluntary_values)
            except ZeroDivisionError:
                times_quicker = 0
            display_strings.append(
                Markup(
                    f"It is approximately <b>{times_quicker:.2f}x</b> <i>({year_difference} years)</i> faster "
                    f"and <b>${total_involuntary_index - total_voluntary_index:,.2f} cheaper</b> "
                    f"to make <b>${weekly_repayments:,.2f} weekly payments</b> "
                    f"<i>(${weekly_repayments * 52:,.2f} Annually)</i>"))
            display_strings.append(Markup(
                f"You would earn approximately <b>${user_hecs_tax.user_income_hecs_tax_amount * year_difference:,.2f}</b> "
                f"over the course of the <b>{year_difference} years</b> you would have been paying mandatory HECS tax"))
            display_strings.append(
                Markup(f"With the combined savings and extra earnings, you would have approximately "
                       f"<span style='color:green'><b>${((user_hecs_tax.user_income_hecs_tax_amount * year_difference) * 0.675) + (total_involuntary_index - total_voluntary_index):,.2f}</b> more in your pocket "
                       f"after <b>{int(len(involuntary_values) / 12)} years</b></span>, compared to <span style='color:red'>$0 if you make no voluntary repayments</span>"))
            display_output = True

            g_sheet_new_row.extend([display_strings[2], display_strings[4], year_difference,
                                    f"${total_involuntary_index - total_voluntary_index:,.2f}",
                                    date_time, timezone])

        except RecursionError:
            if annual_income < user_hecs_tax.tax_brackets_min:
                error_strings.append(Markup(
                    f"Your annual income of <b>${annual_income:,}</b> is not high enough to automatically pay HECS debt tax<br><br>"
                    f"The minimum annual income for automatic repayments is <b>${user_hecs_tax.tax_brackets_min:,.2f}</b><br><br>"
                    f"At a minimum, you should voluntarily repay <b>${(hecs_debt * index_rate) / 52:,.2f} per week (${hecs_debt * index_rate:,.2f} Annually)</b> "
                    f"to negate average annual loan indexation<br><br>"
                    f"A good rule of thumb is to set aside enough money to offset indexation and pay a little extra off the loan. <i>Usually</i> 2-5% of you annual income will cover this<br><br>"
                    f"In this case, <b>2-5%</b> of <u>${annual_income:,.2f}</u> is <b>${annual_income * 0.02:,.2f}-${annual_income * 0.05:,.2f}</b>"))
            else:
                error_strings.append(Markup(
                    f"Your annual income of <b>${annual_income:,.2f}</b> is likely not high enough to repay your HECS debt of <b>${hecs_debt:,.2f}</b> <span style='color:red'>without voluntary repayments</span><br><br>"
                    f"You should voluntarily repay <b>${(hecs_debt * index_rate) / 52:,.2f} per week (${hecs_debt * index_rate:,.2f} Annually)</b> "
                    f"at a minimum to negate average annual loan indexation<br><br>"
                    f"Your specified weekly voluntary repayments of <b>${weekly_repayments:,.2f}</b> total <b>${weekly_repayments * 52:,.2f}</b> annually<br><br>"
                    f"Choosing to <b>not make any voluntary repayments</b> will <b>exponentially increase the amount of time</b> it takes you to pay off your debt!"))

            g_sheet_new_row.extend(["Could Not Calculate", "Could Not Calculate", "Could Not Calculate",
                                    "Could Not Calculate",
                                    date_time, timezone])

    sheet.append_row(g_sheet_new_row, value_input_option='USER_ENTERED')

    return render_template(f"{blueprint_name}.html", form=form, display_strings=display_strings,
                           error_strings=error_strings, display_output=display_output)


def calculate_hecs_repayments(hecs_debt, index_rate, mandatory_hecs_tax_repayment, voluntary_repayment,
                              includes_voluntary_payment, value_list=None, indexed_list=None):
    if value_list is None:
        value_list = []

    if indexed_list is None:
        indexed_list = []

    # If user is making voluntary repayments, set hecs accordingly
    if voluntary_repayment:
        hecs_debt = hecs_debt - voluntary_repayment

    # If it's the 12th cycle, apply indexation to the hecs debt, otherwise just take away the mandatory amount from tax
    if len(value_list) % 12 == 0:
        hecs_debt = (hecs_debt * (index_rate + 1)) - (mandatory_hecs_tax_repayment / 12)
        indexed_list.append(hecs_debt * index_rate)
    else:
        hecs_debt = hecs_debt - (mandatory_hecs_tax_repayment / 12)

    # If there is still more hecs to pay, run the function again
    if hecs_debt > 0:
        value_list.append(hecs_debt)
        calculate_hecs_repayments(hecs_debt, index_rate, mandatory_hecs_tax_repayment, voluntary_repayment,
                                  includes_voluntary_payment,
                                  value_list, indexed_list)
    return value_list, indexed_list


def get_values_from_ato_table(url: str, cut_leading_rows: int = 0):
    table_values = []

    req = requests.get(url)
    soup = BeautifulSoup(req.text, "html.parser")

    # Find text in first table in page (first table is current financial year's rates)
    table_rows = soup.find("tbody").find_all("p")

    row_values = []
    for row_index, row in enumerate(table_rows[2:]):
        if row_index % 2 == 0:  # loop every second row
            for i in strip_characters(row_index, row.text):  # convert values returned to float
                row_values.append(float(i))
        else:
            row_values.append(float(strip_characters(row_index, row.text)[0]))
            table_values.append(row_values[cut_leading_rows:])
            row_values = []

    return table_values


def strip_characters(index, text):
    value_list = []

    string_builder = ""
    for character in text:
        # remove all values that aren't digits, dot points or spaces
        if character.isdigit() or character in [" ", "."]:
            string_builder += character

    # remove % from percentages and split upper and lower bounds into list values
    row_text = string_builder.replace('%', "").split("  ")

    # remove leading space
    if index % 2 == 0:
        if row_text[0].startswith(" "):
            row_text[0] = row_text[0].strip()

        # Add 0 as the very first value of the list
        if len(row_text) == 1:
            row_text.insert(0, '0')

        # if an upper limit doesn't exist, make upper limit equal to previous value
        if len(row_text) == 2 and row_text[1] == "":
            row_text[1] = row_text[0]

        value_list = row_text

    else:  # taxation rate
        if row_text[0]:  # fix 'Nil' being empty after character removal
            row_text[0] = row_text[0].replace(" ", "")
            value_list.append(row_text[0])
        else:
            value_list.append('0')

    return value_list
