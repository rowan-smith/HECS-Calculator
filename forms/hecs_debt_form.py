from flask_wtf import FlaskForm
from wtforms import IntegerField, SubmitField
from wtforms.validators import DataRequired


class HecsDebtForm(FlaskForm):
    annual_income = IntegerField("Annual Income", validators=[DataRequired()])
    hecs_debt = IntegerField("Hecs Debt", validators=[DataRequired()])
    weekly_voluntary_repayments = IntegerField("Weekly Voluntary Repayments", validators=[DataRequired()])
    calculate = SubmitField("Calculate!")
