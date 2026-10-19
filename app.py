import math
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title='RetireSmart | Retirement Calculator', page_icon='🌱', layout='wide')

CURRENCIES = {'AUD': 'A$', 'IDR': 'Rp', 'USD': '$'}

def money(value, currency):
    if not math.isfinite(value):
        return '—'
    decimals = 0 if currency == 'IDR' else 2
    return f"{CURRENCIES[currency]}{value:,.{decimals}f}"

def monthly_growth(annual_percent):
    annual = annual_percent / 100
    if annual <= -1:
        raise ValueError('Annual return must be greater than -100%.')
    return (1 + annual) ** (1 / 12) - 1

def project(current_age, retirement_age, lifespan, savings, contribution, spending_today,
            annual_return, inflation, collect=True):
    """End-of-month contributions, beginning-of-month retirement withdrawals.

    At retirement the first withdrawal is spending_today * (1+inflation)^years_elapsed.
    The final withdrawal is made during the last month before the selected lifespan.
    """
    growth = monthly_growth(annual_return)
    infl = monthly_growth(inflation)
    months_until_retire = round((retirement_age - current_age) * 12)
    months_until_end = round((lifespan - current_age) * 12)
    balance = float(savings)
    depleted_month = None
    rows = []
    annual_opening = balance
    annual_contributions = annual_withdrawals = annual_growth = 0.0
    balance_at_retirement = savings if months_until_retire == 0 else None

    for month in range(months_until_end):
        if month == months_until_retire:
            balance_at_retirement = balance
        before = balance
        if month < months_until_retire:
            earned = balance * growth
            balance += earned + contribution
            annual_contributions += contribution
            annual_growth += earned
        else:
            withdrawal = spending_today * ((1 + infl) ** month)
            balance -= withdrawal
            annual_withdrawals += withdrawal
            if balance < -1e-6 and depleted_month is None:
                depleted_month = month
            # After depletion, no borrowing or negative compounding is assumed.
            earned = max(balance, 0) * growth
            balance += earned
            annual_growth += earned
        if (month + 1) % 12 == 0 and collect:
            rows.append({
                'Age': current_age + (month + 1) // 12,
                'Opening balance': annual_opening,
                'Contributions': annual_contributions,
                'Investment growth': annual_growth,
                'Retirement spending': annual_withdrawals,
                'Closing balance': max(balance, 0),
            })
            annual_opening = balance
            annual_contributions = annual_withdrawals = annual_growth = 0.0
    if balance_at_retirement is None:
        balance_at_retirement = balance
    return {
        'sustainable': depleted_month is None,
        'depletion_age': None if depleted_month is None else current_age + depleted_month / 12,
        'retirement_balance': balance_at_retirement,
        'ending_balance': max(balance, 0),
        'rows': rows,
    }

def minimum_contribution(current_age, retirement_age, lifespan, savings, spending, annual_return, inflation):
    def run(amount):
        return project(current_age, retirement_age, lifespan, savings, amount, spending,
                       annual_return, inflation, collect=False)['sustainable']
    if run(0):
        return 0.0
    hi = max(1.0, spending)
    for _ in range(90):
        if run(hi):
            break
        hi *= 2
    else:
        return None
    lo = 0.0
    for _ in range(48):
        mid = (lo + hi) / 2
        if run(mid):
            hi = mid
        else:
            lo = mid
    return hi

def earliest_retirement(current_age, lifespan, savings, contribution, spending, annual_return, inflation):
    for age in range(current_age, lifespan):
        result = project(current_age, age, lifespan, savings, contribution, spending,
                         annual_return, inflation, collect=False)
        if result['sustainable']:
            return age
    return None

st.title('🌱 RetireSmart')
st.caption('A simple retirement calculator — plan how much to invest or discover when you could retire.')

mode = st.radio('What would you like to calculate?',
                ['How much should I contribute to retire at my target age?',
                 'If I contribute a set amount each month, when can I retire?'],
                horizontal=False)
option_a = mode.startswith('How much')

with st.container(border=True):
    st.subheader('Your retirement plan')
    left, right = st.columns(2)
    with left:
        currency = st.selectbox('Currency', list(CURRENCIES), index=0,
                                help='Currency labels only: amounts are not converted.')
        current_age = st.number_input('Your current age', min_value=16, max_value=110, value=30, step=1)
        lifespan = st.number_input('What age do you expect to live to?', min_value=17,
                                   max_value=120, value=95, step=1,
                                   help='Used only as the end of the retirement projection.')
        savings = st.number_input(f'Existing savings / investments ({currency})',
                                  min_value=0.0, value=10000.0, step=1000.0,
                                  help='Assumed to be invested immediately and grow at your chosen return.')
    with right:
        annual_return = st.number_input('Expected annual investment return (%)',
                                        min_value=-99.0, max_value=50.0, value=7.0, step=0.5)
        inflation = st.number_input('Expected annual inflation (%)',
                                    min_value=-20.0, max_value=30.0, value=2.5, step=0.5)
        spending = st.number_input(f'Desired monthly retirement spending, in today’s money ({currency})',
                                   min_value=0.0, value=5000.0, step=500.0)
        if option_a:
            retirement_age = st.number_input('Target retirement age', min_value=16,
                                             max_value=120, value=55, step=1)
            contribution = None
        else:
            contribution = st.number_input(f'Amount you can invest each month ({currency})',
                                           min_value=0.0, value=2000.0, step=100.0)
            retirement_age = None

if lifespan <= current_age:
    st.error('Your expected lifespan must be greater than your current age.')
    st.stop()
if option_a and retirement_age >= lifespan:
    st.error('You’ll work until you’re dead hahaha 💀 Choose a retirement age below your expected lifespan!')
    st.stop()
if option_a and retirement_age < current_age:
    st.error('Your retirement age cannot be earlier than your current age.')
    st.stop()
if spending <= 0:
    st.info('Enter a positive monthly retirement spending target to calculate your plan.')
    st.stop()

scenarios = [('Lower return', annual_return - 2), ('Base case', annual_return),
             ('Higher return', annual_return + 2)]
results = []
for name, rate in scenarios:
    if rate <= -100:
        results.append({'Scenario': name, 'Return': rate, 'Result': None, 'Projection': None})
        continue
    if option_a:
        amount = minimum_contribution(current_age, retirement_age, lifespan, savings, spending,
                                      rate, inflation)
        # Round up so displayed monthly contribution is itself sufficient.
        if amount is not None:
            amount = math.ceil(amount * (1 if currency == 'IDR' else 100)) / (1 if currency == 'IDR' else 100)
        age = retirement_age
    else:
        age = earliest_retirement(current_age, lifespan, savings, contribution, spending,
                                  rate, inflation)
        amount = contribution
    projection = None if age is None or amount is None else project(
        current_age, age, lifespan, savings, amount, spending, rate, inflation)
    results.append({'Scenario': name, 'Return': rate,
                    'Result': amount if option_a else age, 'Projection': projection})

base = results[1]
st.divider()
st.subheader('Your result')
if base['Result'] is None:
    st.error('You’ll work until you’re dead hahaha 💀 With these inputs, your investments cannot fund retirement before your chosen lifespan. Try increasing your contribution or reducing spending.')
else:
    if option_a:
        st.metric('Minimum monthly investment (base case)', money(base['Result'], currency))
        st.write(f"To retire at **age {retirement_age}**, and fund your desired spending until **age {lifespan}**.")
    else:
        st.metric('Earliest sustainable retirement age (base case)', f"{base['Result']} years old")
        st.write(f"With **{money(contribution, currency)} invested each month**, and your desired spending funded until **age {lifespan}**.")

st.subheader('Investment return sensitivity (±2 percentage points)')
cols = st.columns(3)
for col, entry in zip(cols, results):
    with col:
        with st.container(border=True):
            st.caption(f"{entry['Scenario']} · {entry['Return']:g}% return")
            if entry['Result'] is None:
                st.write('**Not achievable**')
            elif option_a:
                st.write(f"**{money(entry['Result'], currency)}/month**")
            else:
                st.write(f"**Age {entry['Result']}**")

if base['Projection'] is not None:
    projected_spending = spending * (1 + inflation / 100) ** (base['Result'] - current_age if not option_a else retirement_age - current_age)
    m1, m2 = st.columns(2)
    with m1:
        st.metric('Projected investments at retirement', money(base['Projection']['retirement_balance'], currency))
    with m2:
        st.metric('Monthly spending at retirement (future money)', money(projected_spending, currency))

st.subheader('Projected investment balances')
fig = go.Figure()
colors = {'Lower return': '#dc8a44', 'Base case': '#3d9d88', 'Higher return': '#6685dc'}
for entry in results:
    if entry['Projection'] is None:
        continue
    df = pd.DataFrame(entry['Projection']['rows'])
    fig.add_trace(go.Scatter(x=[current_age] + df['Age'].tolist(),
                             y=[savings] + df['Closing balance'].tolist(),
                             mode='lines', name=f"{entry['Scenario']} ({entry['Return']:g}%)",
                             line=dict(color=colors[entry['Scenario']], width=3 if entry['Scenario'] == 'Base case' else 2)))
fig.update_layout(xaxis_title='Age', yaxis_title=f'Investment balance ({currency})',
                  hovermode='x unified', margin=dict(l=12, r=12, t=20, b=20),
                  legend=dict(orientation='h', y=-0.22))
st.plotly_chart(fig, use_container_width=True)

if base['Projection'] is not None:
    st.subheader('Annual projection · base case')
    df = pd.DataFrame(base['Projection']['rows'])
    st.dataframe(df, use_container_width=True, hide_index=True,
                 column_config={c: st.column_config.NumberColumn(c, format='%.0f' if currency == 'IDR' else '%.2f')
                                for c in df.columns if c != 'Age'})
    st.download_button('⬇️ Download annual projection (CSV)',
                       df.to_csv(index=False).encode('utf-8-sig'),
                       file_name='retiresmart_projection.csv', mime='text/csv')

st.divider()
st.caption('Method: nominal annual returns and inflation are converted to effective monthly rates. Contributions are invested at month-end before retirement; retirement withdrawals occur at month-start. Retirement starts at the selected whole-number age, and the final withdrawal occurs in the month before the chosen lifespan. Returns are constant in each scenario. Existing savings are assumed invested. No taxes, fees, pensions, exchange-rate changes, or market volatility are included. The ±2 percentage-point scenarios are sensitivities, not probabilities or guarantees. Educational illustration only, not financial advice.')
