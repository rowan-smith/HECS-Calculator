from flask import render_template, Blueprint

from forms import HecsDebtForm

blueprint_name = "hecs_calculator"

hecs_calculator = Blueprint(blueprint_name, __name__)


@hecs_calculator.route(f'/{blueprint_name}', methods=['GET', 'POST'])
def _hecs_calculator():
    form = HecsDebtForm()
    if form.validate_on_submit():
        print("YES!")
        # HECS LOGIC HERE
        return "ok, wrong way"
    return render_template(f"{blueprint_name}.html", form=form)
