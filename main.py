"""
Business Acquisition Analyzer
Author: Dawson Graditor (dgrad@udel.edu)

You enter the details of a business deal and the site estimates profit and debt
for each year. Then it works out the investor's return (MOIC and IRR) and gives
the deal a rating. This is a simple model for learning, not financial advice.

Things I used that we didnt cover in class:
  - "{:,.0f}".format(x) formats numbers (used in money, percent, multiple)
  - text.strip() takes off spaces at the beginning and end of text
  - my_list.pop(i) removes whatever item is at position i
  - x ** (1 / n) gives the n-th root, which I use for IRR
  - Header, Table, Row, HorizontalRule, Text are Drafter components for
    titles, tables, buttons next to each other, lines, and text
  - Argument("deal_index", position) tells the route which deal the user
    clicked on
  - set_website_title changes the tab title and hide_debug_information
    hides Drafter's debug panel
"""
from dataclasses import dataclass
from drafter import *
from bakery import assert_equal

set_site_information(
    author="dgrad@udel.edu (Dawson Graditor)",
    description="""Business Acquisition Analyzer: enter a deal's assumptions,
    see a year-by-year projection of profit and debt, and get the investor's
    MOIC, IRR, and a Strong Buy / Maybe / Pass rating. Compare saved deals
    to find the best one.""",
    sources=["Official Drafter documentation",
             "Claude (AI) was used to help write and explain the code. "
             "The full conversations are uploaded to this repository.",
             "CFI free LBO guides, for checking the finance logic"],
    planning=["week10_brainstorm.docx", "week11_design.docx"],
    links=["https://github.com/dgraditor07/business-acquisition-analyzer",
           "https://REPLACE-WITH-YOUR-VIDEO-URL"]
)
hide_debug_information()
set_website_title("Business Acquisition Analyzer")

# ---------- Global CONSTANTS (allowed; global variables are not) ----------
INDUSTRIES = ["HVAC", "Plumbing", "Cleaning", "Landscaping", "Med Spa",
              "Contractor", "Other"]
YEAR_OPTIONS = ["3", "5", "7"]
SORT_OPTIONS = ["IRR", "MOIC"]
MAYBE_RANGE = 0.05      # "Maybe" = within 5 percentage points below target
NO_DEAL_SELECTED = -1   # selected_index value meaning "no deal is open"
DEFAULT_TARGET_IRR = 0.20
DIGITS = "0123456789"


# ---------- Dataclasses ----------
@dataclass
class Deal:
    """Holds the info for one business deal. Percentages are stored as decimals (20% = 0.20)."""
    name: str
    industry: str
    revenue: float
    ebitda: float
    purchase_price: float
    debt_percent: float
    interest_rate: float
    growth_rate: float
    exit_multiple: float
    years_held: int
    notes: str


@dataclass
class State:
    """Stuff the site needs to keep track of between pages.
    deals: the saved deals (updated when you save, edit, or delete one)
    selected_index: which deal is open (changes when you view, edit, or delete)
    target_irr: the return the user wants (changed by save_settings)
    sort_by: "IRR" or "MOIC" on the Compare page (changed by save_settings)
    error_message: what went wrong with the input, gets set or cleared when saving"""
    deals: list[Deal]
    selected_index: int
    target_irr: float
    sort_by: str
    error_message: str


# ---------- Math helpers ----------
def equity_invested(deal: Deal) -> float:
    """Figures out how much of the buyers own money goes into the deal."""
    return deal.purchase_price * (1 - deal.debt_percent)


def project_years(deal: Deal) -> list[list[float]]:
    """Makes one row for each year: [year, ebitda, interest, paid, debt left].
    Profit grows each year, then interest comes out and any cash left goes to the loan."""
    rows = []
    ebitda = deal.ebitda
    debt = deal.purchase_price * deal.debt_percent
    for year in range(1, deal.years_held + 1):
        ebitda = ebitda * (1 + deal.growth_rate)
        interest = debt * deal.interest_rate
        leftover_cash = ebitda - interest
        if leftover_cash > debt:
            # Only pay off what is left, so debt never goes below $0
            paid = debt
        else:
            # If leftover_cash is negative, "paid" is negative, which means
            # the unpaid interest gets added onto the debt
            paid = leftover_cash
        debt = debt - paid
        rows.append([year, ebitda, interest, paid, debt])
    return rows


def sale_price(deal: Deal) -> float:
    """Estimates the sale price using the last year's EBITDA times the exit multiple."""
    final_ebitda = project_years(deal)[-1][1]
    return final_ebitda * deal.exit_multiple


def exit_equity(deal: Deal) -> float:
    """Works out what the investor gets after the remaining debt comes out
    of the sale price. The lowest they can get back is $0."""
    debt_left = project_years(deal)[-1][4]
    leftover = sale_price(deal) - debt_left
    if leftover < 0:
        # The investor can lose their whole investment, but not more than that
        return 0.0
    return leftover


def calculate_moic(deal: Deal) -> float:
    """Gets MOIC by dividing the money you get back by what you put in."""
    return exit_equity(deal) / equity_invested(deal)


def calculate_irr(deal: Deal) -> float:
    """Works out the yearly return using MOIC ** (1 / years) - 1.
    If the investor gets nothing back it returns -1.0 for a total loss."""
    moic = calculate_moic(deal)
    if moic <= 0:
        return -1.0
    return moic ** (1 / deal.years_held) - 1


def rate_deal(irr: float, target_irr: float) -> str:
    """Picks "Strong Buy", "Maybe", or "Pass" based on how the IRR compares to the target."""
    if irr >= target_irr:
        return "Strong Buy"
    elif irr >= target_irr - MAYBE_RANGE:
        return "Maybe"
    return "Pass"


def deal_score(deal: Deal, sort_by: str) -> float:
    """Gets the IRR or MOIC depending on what the deals are ranked by."""
    if sort_by == "MOIC":
        return calculate_moic(deal)
    return calculate_irr(deal)


def find_best_index(deals: list[Deal], sort_by: str) -> int:
    """Finds the spot of the highest scoring deal, or NO_DEAL_SELECTED if theres none."""
    best_index = NO_DEAL_SELECTED
    best_score = 0.0
    for position in range(len(deals)):
        score = deal_score(deals[position], sort_by)
        if best_index == NO_DEAL_SELECTED or score > best_score:
            best_index = position
            best_score = score
    return best_index


# ---------- Formatting helpers ----------
def money(amount: float) -> str:
    """Shows a number in whole dollars with commas, like $1,234,567."""
    return "${:,.0f}".format(amount)


def percent(rate: float) -> str:
    """Turns a decimal into percent text, so 0.2346 shows up as 23.5%."""
    return "{:.1f}%".format(rate * 100)


def multiple(value: float) -> str:
    """Shows the MOIC with two decimal places and an x, like 3.83x."""
    return "{:.2f}x".format(value)


def as_input_text(value: float) -> str:
    """Turns a number into text for the form box so 5.0 shows up as "5"."""
    if value == int(value):
        return str(int(value))
    return str(round(value, 4))


# ---------- Input checking helpers ----------
def clean_number_text(text: str) -> str:
    """Takes out spaces, dollar signs, commas and percent signs from what was typed."""
    cleaned = ""
    for character in text:
        if character not in " $,%":
            cleaned = cleaned + character
    return cleaned


def is_number(text: str) -> bool:
    """Checks if the cleaned text is zero or a positive number, like "12" or "4.5"."""
    cleaned = clean_number_text(text)
    if cleaned == "" or cleaned == ".":
        return False
    dot_count = 0
    for character in cleaned:
        if character == ".":
            dot_count = dot_count + 1
        elif character not in DIGITS:
            return False
    return dot_count <= 1


def to_number(text: str) -> float:
    """Cleans up the text and converts it to a float."""
    return float(clean_number_text(text))


def check_deal_inputs(name: str, revenue: str, ebitda: str, price: str,
                      debt_percent: str, interest_rate: str,
                      growth_rate: str, exit_multiple: str) -> str:
    """Gives an error message for the first bad input, or "" if everything looks ok."""
    if name.strip() == "":
        return "Please give the deal a name."
    number_boxes = [["Revenue", revenue], ["EBITDA", ebitda],
                    ["Purchase price", price], ["Debt %", debt_percent],
                    ["Interest rate", interest_rate], ["Growth rate", growth_rate],
                    ["Exit multiple", exit_multiple]]
    for box in number_boxes:
        if not is_number(box[1]):
            return box[0] + " must be a positive number (no letters)."
    if to_number(price) <= 0 or to_number(ebitda) <= 0:
        return "Purchase price and EBITDA must be greater than 0."
    if to_number(exit_multiple) <= 0:
        return "Exit multiple must be greater than 0."
    if to_number(debt_percent) >= 100:
        return "Debt % must be less than 100 (you need some of your own money)."
    return ""


def build_deal(name: str, industry: str, revenue: str, ebitda: str,
               price: str, debt_percent: str, interest_rate: str,
               growth_rate: str, exit_multiple: str, years_held: str,
               notes: str) -> Deal:
    """Makes a Deal out of whats in the form. A percent like 60 gets stored as 0.60."""
    return Deal(name.strip(), industry, to_number(revenue), to_number(ebitda),
                to_number(price), to_number(debt_percent) / 100,
                to_number(interest_rate) / 100, to_number(growth_rate) / 100,
                to_number(exit_multiple), int(years_held), notes)


def deal_to_form_values(deal: Deal) -> list[str]:
    """Turns the saved deal values into text in the same order as the boxes on the form."""
    return [deal.name, deal.industry, as_input_text(deal.revenue),
            as_input_text(deal.ebitda), as_input_text(deal.purchase_price),
            as_input_text(deal.debt_percent * 100),
            as_input_text(deal.interest_rate * 100),
            as_input_text(deal.growth_rate * 100),
            as_input_text(deal.exit_multiple), str(deal.years_held),
            deal.notes]


def empty_form_values() -> list[str]:
    """Gives the form its starting values when adding a new deal."""
    return ["", "HVAC", "", "", "", "60", "8", "5", "5", "5", ""]


# ---------- Page-building helpers ----------
def navigation_bar() -> list:
    """Puts together the buttons that go at the bottom of each page."""
    return [HorizontalRule(),
            Button("Home", index), Button("Add Deal", add_deal),
            Button("Compare", compare), Button("Settings", settings)]


def deal_form(state: State, title: str, submit_text: str, submit_route: str,
              values: list[str]) -> Page:
    """Builds the form for adding or editing a deal. submit_route is where the Save button goes."""
    content = [Header(title)]
    if state.error_message != "":
        content.append(Text("Error: " + state.error_message))
    content = content + [
        "Deal name:", TextBox("name", values[0]),
        "Industry:", SelectBox("industry", INDUSTRIES, values[1]),
        "Yearly revenue ($):", TextBox("revenue", values[2]),
        "Yearly profit / EBITDA ($):", TextBox("ebitda", values[3]),
        "Purchase price ($):", TextBox("price", values[4]),
        "Percent paid with debt (example: 60):",
        TextBox("debt_percent", values[5]),
        "Loan interest rate % (example: 8):",
        TextBox("interest_rate", values[6]),
        "Yearly EBITDA growth % (example: 5):",
        TextBox("growth_rate", values[7]),
        "Exit multiple (sale price = final EBITDA x this):",
        TextBox("exit_multiple", values[8]),
        "Years held:", SelectBox("years_held", YEAR_OPTIONS, values[9]),
        "Notes:", TextArea("notes", values[10]),
        Button(submit_text, submit_route),
    ]
    return Page(state, content + navigation_bar())


# ---------- Routes ----------
@route
def index(state: State) -> Page:
    """Shows the home page with each deal's IRR, MOIC, rating and buttons."""
    content = [Header("Business Acquisition Analyzer"),
               "Enter a deal's assumptions to see the investor's return.",
               "Your target IRR: " + percent(state.target_irr)]
    if len(state.deals) == 0:
        content.append("No deals saved yet. Add one to get started!")
    for position in range(len(state.deals)):
        deal = state.deals[position]
        irr = calculate_irr(deal)
        content.append(Header(deal.name + " (" + deal.industry + ")", 3))
        content.append("IRR " + percent(irr) + " | MOIC "
                       + multiple(calculate_moic(deal)) + " | "
                       + rate_deal(irr, state.target_irr))
        content.append(Row(
            Button("View", view_results, [Argument("deal_index", position)]),
            Button("Edit", edit_deal, [Argument("deal_index", position)]),
            Button("Delete", delete_deal, [Argument("deal_index", position)])
        ))
    content.append(Text("Educational estimate only, not financial advice."))
    return Page(state, content + navigation_bar())


@route
def add_deal(state: State) -> Page:
    """Opens a fresh form where you can enter a new deal."""
    state.error_message = ""
    return deal_form(state, "Add a Deal", "Save Deal", "save_deal",
                     empty_form_values())


@route
def save_deal(state: State, name: str, industry: str, revenue: str,
              ebitda: str, price: str, debt_percent: str,
              interest_rate: str, growth_rate: str, exit_multiple: str,
              years_held: str, notes: str) -> Page:
    """Saves the new deal if the form checks out, otherwise it shows an error."""
    typed = [name, industry, revenue, ebitda, price, debt_percent,
             interest_rate, growth_rate, exit_multiple, years_held, notes]
    state.error_message = check_deal_inputs(name, revenue, ebitda, price,
                                            debt_percent, interest_rate,
                                            growth_rate, exit_multiple)
    if state.error_message != "":
        return deal_form(state, "Add a Deal", "Save Deal", "save_deal", typed)
    state.deals.append(build_deal(name, industry, revenue, ebitda, price,
                                  debt_percent, interest_rate, growth_rate,
                                  exit_multiple, years_held, notes))
    return view_results(state, len(state.deals) - 1)


@route
def view_results(state: State, deal_index: int) -> Page:
    """Shows the year by year numbers for one deal, plus its sale price, MOIC, IRR and rating."""
    state.selected_index = deal_index
    deal = state.deals[deal_index]
    table_rows = [["Year", "EBITDA", "Interest", "Debt Paid", "Debt Left"]]
    warnings = []
    for row in project_years(deal):
        table_rows.append([str(row[0]), money(row[1]), money(row[2]),
                           money(row[3]), money(row[4])])
        if row[2] > row[1]:
            warnings.append(Text("Warning: in year " + str(row[0])
                                 + ", interest is bigger than profit, so "
                                 + "the business can't cover its loan."))
    irr = calculate_irr(deal)
    margin = "N/A"
    if deal.revenue > 0:
        margin = percent(deal.ebitda / deal.revenue)
    content = [
        Header("Results: " + deal.name),
        "Industry: " + deal.industry + " | EBITDA margin: " + margin,
        Table(table_rows),
        "Your money in (equity): " + money(equity_invested(deal)),
        "Loan amount: " + money(deal.purchase_price * deal.debt_percent),
        "Estimated sale price: " + money(sale_price(deal)),
        "Your money back: " + money(exit_equity(deal)),
        "MOIC: " + multiple(calculate_moic(deal)),
        "IRR: " + percent(irr) + " (target " + percent(state.target_irr) + ")",
        Header("Rating: " + rate_deal(irr, state.target_irr), 2),
    ]
    if deal.notes != "":
        content.append("Notes: " + deal.notes)
    content = content + warnings
    content.append(Button("Edit this deal", edit_deal,
                          [Argument("deal_index", deal_index)]))
    return Page(state, content + navigation_bar())


@route
def edit_deal(state: State, deal_index: int) -> Page:
    """Opens the form with the deal's saved info already filled in."""
    state.selected_index = deal_index
    state.error_message = ""
    return deal_form(state, "Edit: " + state.deals[deal_index].name,
                     "Save Changes", "update_deal",
                     deal_to_form_values(state.deals[deal_index]))


@route
def update_deal(state: State, name: str, industry: str, revenue: str,
                ebitda: str, price: str, debt_percent: str,
                interest_rate: str, growth_rate: str, exit_multiple: str,
                years_held: str, notes: str) -> Page:
    """Checks the edited form and saves the changes to the open deal if everything looks ok."""
    typed = [name, industry, revenue, ebitda, price, debt_percent,
             interest_rate, growth_rate, exit_multiple, years_held, notes]
    state.error_message = check_deal_inputs(name, revenue, ebitda, price,
                                            debt_percent, interest_rate,
                                            growth_rate, exit_multiple)
    if state.error_message != "":
        return deal_form(state, "Edit Deal", "Save Changes", "update_deal",
                         typed)
    state.deals[state.selected_index] = build_deal(
        name, industry, revenue, ebitda, price, debt_percent, interest_rate,
        growth_rate, exit_multiple, years_held, notes)
    return view_results(state, state.selected_index)


@route
def delete_deal(state: State, deal_index: int) -> Page:
    """Removes the deal and adjusts selected_index if the open deal moved or was deleted."""
    state.deals.pop(deal_index)
    if state.selected_index == deal_index:
        state.selected_index = NO_DEAL_SELECTED
    elif state.selected_index > deal_index:
        # Every deal after the deleted one moved down one spot
        state.selected_index = state.selected_index - 1
    return index(state)


@route
def compare(state: State) -> Page:
    """Shows all the deals in a table and points out which one scores the highest."""
    content = [Header("Compare Deals"),
               "Ranking by: " + state.sort_by + " (change this in Settings)"]
    best_index = find_best_index(state.deals, state.sort_by)
    if best_index == NO_DEAL_SELECTED:
        content.append("No deals to compare yet.")
        return Page(state, content + navigation_bar())
    rows = [["Deal", "Industry", "MOIC", "IRR", "Rating"]]
    for deal in state.deals:
        irr = calculate_irr(deal)
        rows.append([deal.name, deal.industry,
                     multiple(calculate_moic(deal)), percent(irr),
                     rate_deal(irr, state.target_irr)])
    content.append(Table(rows))
    content.append(Header("Best deal: " + state.deals[best_index].name, 2))
    content.append(Button("View best deal", view_results,
                          [Argument("deal_index", best_index)]))
    return Page(state, content + navigation_bar())


@route
def settings(state: State) -> Page:
    """Shows the page where you can change the target IRR and what deals are ranked by."""
    content = [Header("Settings")]
    if state.error_message != "":
        content.append(Text("Error: " + state.error_message))
    content = content + [
        "Target IRR % (example: 20):",
        TextBox("target_irr", as_input_text(state.target_irr * 100)),
        "Rank deals on the Compare page by:",
        SelectBox("sort_by", SORT_OPTIONS, state.sort_by),
        Button("Save Settings", save_settings),
    ]
    return Page(state, content + navigation_bar())


@route
def save_settings(state: State, target_irr: str, sort_by: str) -> Page:
    """Saves the target IRR and sort order, or shows an error if the target isnt valid."""
    if not is_number(target_irr) or to_number(target_irr) > 100:
        state.error_message = "Target IRR must be a number from 0 to 100."
        return settings(state)
    state.error_message = ""
    state.target_irr = to_number(target_irr) / 100
    state.sort_by = sort_by
    return index(state)


# ---------- Sample data (functions, so there are no global variables) ----------
def make_sample_deals() -> list[Deal]:
    """Makes three example deals with one of each rating, Strong Buy, Maybe and Pass."""
    return [
        Deal("Frederick Heating Co", "HVAC", 2000000, 400000, 2000000,
             0.60, 0.08, 0.05, 6, 5, "Strong local reputation"),
        Deal("Sparkle Cleaners", "Cleaning", 800000, 120000, 600000,
             0.70, 0.10, 0.00, 3.2, 5, "Owner wants to retire"),
        Deal("Overpriced Plumbing", "Plumbing", 1500000, 150000, 2000000,
             0.80, 0.10, 0.00, 4, 5, "Asking price looks too high"),
    ]


def make_test_state() -> State:
    """Sets up a fresh State with the sample deals so the tests can use it."""
    return State(make_sample_deals(), NO_DEAL_SELECTED, DEFAULT_TARGET_IRR,
                 "IRR", "")


def make_selected_state(selected: int) -> State:
    """Makes a test State with the deal at the given index already open."""
    return State(make_sample_deals(), selected, DEFAULT_TARGET_IRR, "IRR", "")


def sample_hvac_deal() -> Deal:
    """Grabs the Frederick Heating Co deal to use in the tests."""
    return make_sample_deals()[0]


# ---------- Unit tests: helpers ----------
# Year 1 checked by hand and in Excel for Frederick Heating Co:
# debt 1,200,000, EBITDA 420,000, interest 96,000, debt left 876,000
assert_equal(equity_invested(sample_hvac_deal()), 800000.0)
assert_equal(project_years(sample_hvac_deal())[0],
             [1, 420000.0, 96000.0, 324000.0, 876000.0])
assert_equal(len(project_years(sample_hvac_deal())), 5)
assert_equal(round(calculate_moic(sample_hvac_deal()), 2), 3.83)
assert_equal(round(calculate_irr(sample_hvac_deal()), 3), 0.308)
assert_equal(rate_deal(0.25, 0.20), "Strong Buy")
assert_equal(rate_deal(0.17, 0.20), "Maybe")
assert_equal(rate_deal(0.10, 0.20), "Pass")
assert_equal(rate_deal(calculate_irr(make_sample_deals()[2]), 0.20), "Pass")
assert_equal(exit_equity(make_sample_deals()[2]), 0.0)
assert_equal(find_best_index(make_sample_deals(), "IRR"), 0)
assert_equal(find_best_index([], "IRR"), NO_DEAL_SELECTED)
assert_equal(money(1234567.4), "$1,234,567")
assert_equal(percent(0.2346), "23.5%")
assert_equal(multiple(3.834), "3.83x")
assert_equal(as_input_text(5.0), "5")
assert_equal(clean_number_text("$1,000"), "1000")
assert_equal(is_number("4.5"), True)
assert_equal(is_number("abc"), False)
assert_equal(is_number(""), False)
assert_equal(is_number("-5"), False)
assert_equal(is_number("1.2.3"), False)
assert_equal(check_deal_inputs("A", "1", "1", "1", "50", "8", "5", "5"), "")
assert_equal(check_deal_inputs(" ", "1", "1", "1", "50", "8", "5", "5"),
             "Please give the deal a name.")
assert_equal(check_deal_inputs("A", "1", "1", "1", "100", "8", "5", "5"),
             "Debt % must be less than 100 (you need some of your own money).")
assert_equal(build_deal("A", "HVAC", "100", "50", "200", "60", "8", "5", "4",
                        "3", "").debt_percent, 0.6)

# ---------- Unit tests: routes (at least one per route) ----------
assert_equal("No deals saved yet. Add one to get started!" in index(
    State([], NO_DEAL_SELECTED, 0.20, "IRR", "")).content, True)
assert_equal(add_deal(make_test_state()).state.error_message, "")
assert_equal(len(save_deal(make_test_state(), "New Co", "HVAC", "500000",
                           "100000", "400000", "50", "8", "5", "5", "5",
                           "").state.deals), 4)
assert_equal(save_deal(make_test_state(), "New Co", "HVAC", "abc", "100000",
                       "400000", "50", "8", "5", "5", "5",
                       "").state.error_message,
             "Revenue must be a positive number (no letters).")
assert_equal(view_results(make_test_state(), 1).state.selected_index, 1)
assert_equal(edit_deal(make_test_state(), 2).state.selected_index, 2)
assert_equal(update_deal(make_selected_state(0), "Renamed Co", "HVAC",
                         "2000000", "400000", "2000000", "60", "8", "5",
                         "6", "5", "").state.deals[0].name, "Renamed Co")
assert_equal(delete_deal(make_selected_state(2), 0).state.selected_index, 1)
assert_equal(len(delete_deal(make_test_state(), 0).state.deals), 2)
assert_equal(Header("Best deal: Frederick Heating Co", 2) in
             compare(make_test_state()).content, True)
assert_equal("No deals to compare yet." in compare(
    State([], NO_DEAL_SELECTED, 0.20, "IRR", "")).content, True)
assert_equal(settings(make_test_state()).state.sort_by, "IRR")
assert_equal(save_settings(make_test_state(), "15", "MOIC").state.target_irr,
             0.15)
assert_equal(save_settings(make_test_state(), "lots", "IRR").state.error_message,
             "Target IRR must be a number from 0 to 100.")

start_server(make_test_state())
