import uvicorn
from jinja2 import Template
from markupsafe import Markup
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import HTMLResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette_wtf import CSRFProtectMiddleware

from forms.hecs_debt_form import HecsDebtForm
from utils.UserHecsCalculations import UserHecsTax
from views.hecs_calculator import get_values_from_ato_table, calculate_hecs_repayments

ATO_HELP_THRESHOLD_URL = "https://www.ato.gov.au/Rates/HELP,-TSL-and-SFSS-repayment-thresholds-and-rates/"
ATO_HELP_INDEXATION_URL = "https://www.ato.gov.au/Rates/Study-and-training-loan-indexation-rates/"

templates = Jinja2Templates(directory='templates')

app = Starlette(debug=True, middleware=[Middleware(SessionMiddleware, secret_key='***REPLACEME1***'),
                                        Middleware(CSRFProtectMiddleware, csrf_secret='***REPLACEME2***')])
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.route('/')
async def homepage(request):
    return HTMLResponse("""<p>Links:</p>

<ul>
  <li><a href="/HECS">HECS Information</a></li>
  <li><a href="/HECS/calculator">HECS Calculator</a></li>
</ul>""")


@app.route('/HECS')
async def homepage(request):
    template = "home.html"
    context = {"request": request}
    return templates.TemplateResponse(template, context)


@app.route('/HECS/calculator', methods=['GET', 'POST'])
async def calculator(request):
    form = await HecsDebtForm.from_formdata(request)
    display_strings = []
    error_strings = []
    display_output = False

    if await form.validate_on_submit():
        income_threshold_brackets = get_values_from_ato_table(ATO_HELP_THRESHOLD_URL)
        yearly_indexation_rates = get_values_from_ato_table(ATO_HELP_INDEXATION_URL, 2)

        # Set variables based on form data input
        annual_income = form.annual_income.data
        hecs_debt = form.hecs_debt.data
        weekly_repayments = form.weekly_voluntary_repayments.data
        monthly_repayments = (weekly_repayments * 52) / 12

        user_hecs_tax = UserHecsTax(annual_income, income_threshold_brackets, yearly_indexation_rates)
        index_rate = user_hecs_tax.average_yearly_indexation_rate

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

    t = templates.get_template("hecs_calculator.html")
    html = t.render(form=form, display_strings=display_strings, error_strings=error_strings, display_output=display_output)
    return HTMLResponse(html)
