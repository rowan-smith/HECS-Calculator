from bs4 import BeautifulSoup
import requests


class UserHecsTax:

    def __init__(self, annual_income: int, income_threshold_brackets: list, yearly_indexation_rates: list):
        # user info
        self.user_annual_income: int = annual_income
        self.user_income_hecs_tax_amount: int = 0
        self.user_tax_bracket_tax_rate: int = 0

        # brackets
        self._tax_threshold_brackets: list = income_threshold_brackets
        self._tax_brackets: list = [number[1] for number in income_threshold_brackets]
        self._tax_brackets_rates: list = [number[2] for number in income_threshold_brackets]

        # max and min tax brackets
        self._tax_bracket_max: int = max(self._tax_brackets)
        self._tax_bracket_min: int = min(self._tax_brackets)
        self._tax_bracket_rate_max: int = max(self._tax_brackets_rates)
        self._tax_bracket_rate_min: int = min(self._tax_brackets_rates)

        # indexation rate
        self.yearly_indexation_rates = yearly_indexation_rates
        self.average_yearly_indexation_rate = 0

        # calculation on class creation
        self._find_user_tax_bracket()
        self._calculate_user_hecs_tax_amount()
        self._calculate_average_yearly_indexation_rate()

    def _find_user_tax_bracket(self):
        for bracket in self._tax_threshold_brackets:
            bracket_minimum = int(bracket[0])  # min of tax bracket
            bracket_maximum = int(bracket[1])  # max of tax bracket

            # If annual income within a bracket, set the bracket tax rate
            if bracket_minimum < self.user_annual_income < bracket_maximum:
                self.user_tax_bracket_tax_rate = bracket[2]

            # If income is more than the max bracket, set the tax rate to the max tax rate
            elif self.user_annual_income > self._tax_bracket_max:
                self.user_tax_bracket_tax_rate = self._tax_bracket_rate_max

            # If income is less than the min bracket, set the tax rate to the min tax rate
            elif self.user_annual_income < self._tax_bracket_min:
                self.user_tax_bracket_tax_rate = self._tax_bracket_rate_min

    def _calculate_user_hecs_tax_amount(self):
        # If user income is above the max bracket amount, set the tax amount based on the max tax rate
        if self.user_annual_income > self._tax_bracket_max:
            self.user_income_hecs_tax_amount = self.user_annual_income / (100 / self._tax_bracket_rate_max)

        else:
            bracket_tax_rate = self.user_tax_bracket_tax_rate
            # If user income is below minimum repayment threshold, pass the error
            try:
                self.user_income_hecs_tax_amount = self.user_annual_income / (100 / bracket_tax_rate)
            except ZeroDivisionError:
                pass

    def _calculate_average_yearly_indexation_rate(self):
        yearly_indexation_sum = sum([index[0] for index in self.yearly_indexation_rates])
        yearly_indexation_length = len(self.yearly_indexation_rates)

        self.average_yearly_indexation_rate = (yearly_indexation_sum / yearly_indexation_length) / 100


class TableValuesFromURL:

    def __init__(self, url: str):
        # seen
        self.table_values = []
        self.url = url

        # request and parse
        req = requests.get(url)
        self._soup = BeautifulSoup(req.text, "html.parser")

        # called on created
        self._get_table_rows()
        self._convert_table_rows_to_default_type()

    def _get_table_rows(self, table_element: str = "tbody", row_element: str = "p"):
        table_rows = self._soup.find(table_element).find_all(row_element)

    def _convert_table_rows_to_default_type(self):
        pass
