from flask_wtf import FlaskForm
from wtforms import IntegerField, SubmitField
from wtforms.validators import DataRequired, NumberRange


class HecsDebtForm(FlaskForm):
    number_error = "<span style='color:red'>Please enter a positive number</span>"
    # non_numeric_error = "<span style='color:red'>Please only enter numbers</span>"

    annual_income = IntegerField("Annual Income", validators=[DataRequired(message=number_error),
                                                              NumberRange(min=0, message=number_error)])

    hecs_debt = IntegerField("Hecs Debt", validators=[DataRequired(message=number_error),
                                                      NumberRange(min=0, message=number_error)])

    weekly_voluntary_repayments = IntegerField("Weekly Voluntary Repayments",
                                               validators=[DataRequired(message=number_error),
                                                           NumberRange(min=0, message=number_error)])
    calculate = SubmitField("Calculate!")
