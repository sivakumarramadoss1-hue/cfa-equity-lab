import math
import json
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Siva's Equity Lab", page_icon="📈", layout="wide")


def forecast(d0, rates, r, terminal_g):
    rows = []
    dividend = d0
    for year, growth in enumerate(rates, 1):
        dividend *= 1 + growth
        rows.append({'Year': year, 'Growth': growth, 'Dividend': dividend,
                     'Discount factor': 1 / (1 + r) ** year,
                     'PV dividend': dividend / (1 + r) ** year})
    n = len(rates)
    tv = dividend * (1 + terminal_g) / (r - terminal_g)
    pvtv = tv / (1 + r) ** n
    return sum(row['PV dividend'] for row in rows) + pvtv, rows, tv, pvtv


def h_value(d0, high, stable, years, r):
    return d0 * ((1 + stable) + years / 2 * (high - stable)) / (r - stable)


def value_for(model, d0, high, stable, n, m, middle, transition, custom, r):
    if model == 'Zero growth':
        return d0 / r, [], None, None
    if model == 'Gordon growth':
        return d0 * (1 + stable) / (r - stable), [], None, None
    if model == 'H-model':
        return h_value(d0, high, stable, n, r), [], None, None
    if model == 'Two stage':
        rates = [high] * n
    elif model == 'Three stage':
        fade = [high + (stable - high) * (j + 1) / m for j in range(m)]
        rates = [high] * n + (fade if transition == 'Linear fade' else [middle] * m)
    else:
        # Explicit annual dividend amounts, including years with no dividends.
        rows = [{'Year': i, 'Dividend': d, 'Discount factor': 1/(1+r)**i,
                 'PV dividend': d/(1+r)**i} for i, d in enumerate(custom, 1)]
        tv = custom[-1] * (1 + stable) / (r - stable)
        pvtv = tv / (1 + r) ** len(custom)
        return sum(x['PV dividend'] for x in rows) + pvtv, rows, tv, pvtv
    return forecast(d0, rates, r, stable)


st.title("📈 Siva's Equity Valuation Lab")
st.caption('Learn dividend discount valuation by changing assumptions and following the cash flows.')
company = st.sidebar.selectbox('Case study', ['Apple (AAPL)', 'Fictional company'])
apple = company == 'Apple (AAPL)'
currency = '$' if apple else '₹'
st.caption('Build: Apple Lab v1 • 25 October 2026')
if apple:
    st.subheader('Apple · Dividend valuation playground')
    st.info('USD per share • Dividend history snapshot through 13 August 2026 • Annual end-of-year model • No live price feed')
    st.write('Start with Apple’s actual dividends, choose a model, and change the sidebar assumptions. All six models update together.')
    st.warning('A dividend-only model captures cash dividends. Apple also returns capital through buybacks, so a low DDM value alone does not establish that Apple is overvalued. These results are equity values, not enterprise values.')
    with st.expander('Apple dividend history and starting point', expanded=True):
        history = pd.DataFrame({'Calendar year': [2021, 2022, 2023, 2024, 2025],
                                'Dividend per share ($)': [.865, .91, .95, .99, 1.03]})
        history['Growth (%)'] = history['Dividend per share ($)'].pct_change() * 100
        st.dataframe(history.set_index('Calendar year').style.format(
            {'Dividend per share ($)': '${:.3f}', 'Growth (%)': '{:.2f}%'}, na_rep='—'), use_container_width=True)
        st.line_chart(history.set_index('Calendar year')[['Dividend per share ($)']])
        cagr = (1.03 / .865) ** (1/4) - 1
        a, b, c = st.columns(3)
        a.metric('2021–2025 dividend CAGR', f'{cagr:.2%}')
        b.metric('Trailing four payments', '$1.06')
        c.metric('Latest quarterly rate × 4', '$1.08')
        st.caption('Trailing payments: Nov 2025 $0.26, Feb 2026 $0.26, May 2026 $0.27, Aug 2026 $0.27. Default D₀ is the annualized $0.27 quarterly run rate, not calendar 2025 dividends or trailing dividends. Quarterly payments are simplified into annual year-end cash flows.')
        st.markdown('[Source: Apple dividend history](https://investor.apple.com/dividend-history/)')
else:
    st.info('Fictional company • Annual dividends per share • End-of-year payments • Constant required return • Learning tool')
with st.sidebar:
    st.header('Company assumptions')
    basis = st.selectbox('Dividend starting point', ['Latest quarterly rate × 4', 'Trailing four payments', 'Calendar 2025', 'Custom']) if apple else 'Custom'
    initial_dividend = {'Latest quarterly rate × 4': 1.08, 'Trailing four payments': 1.06, 'Calendar 2025': 1.03, 'Custom': 1.08 if apple else 10.0}[basis]
    d0 = st.number_input(f'Annual dividend D₀ ({currency} per share)', min_value=0.0, value=initial_dividend, step=0.01 if apple else 1.0, key=f'dividend_{company}_{basis}')
    price = st.number_input(f'Comparison share price ({currency}) — enter your quote', min_value=0.01, value=250.0 if apple else 200.0, step=1.0, key=f'price_{company}')
    st.caption('Price is an editable illustration, not a fetched market quote.')
    shares = st.number_input('Shares outstanding (billions) — your assumption', min_value=0.001, value=15.0, step=0.1)
    st.caption('15.0 billion is a rounded illustration. Enter a dated share count to estimate total equity value. Share count stays constant in these models.')
    r = st.number_input('Required return r (%)', min_value=0.1, max_value=100.0, value=10.0, step=0.5) / 100
    stable = st.number_input('Stable growth g (%)', min_value=-50.0, max_value=50.0, value=5.0, step=0.5) / 100
    high = st.number_input('Initial growth (%)', min_value=-50.0, max_value=100.0, value=15.0, step=1.0) / 100
    n = st.slider('Initial stage / H-model fade years', 1, 20, 5)
    m = st.slider('Three-stage transition years', 1, 15, 5)
    transition = st.selectbox('Three-stage transition', ['Linear fade', 'Constant middle growth'])
    middle = st.number_input('Middle-stage growth (%)', min_value=-50.0, max_value=100.0, value=8.0) / 100
    raw = st.text_input(f'Multistage: annual dividend forecasts ({currency})', '1.13, 1.19, 1.25, 1.31, 1.38' if apple else '10, 12, 15, 17, 18', key=f'custom_{company}')
    st.caption('Comma-separated amounts D₁ … Dₙ, not growth rates. These override D₀ in the multistage model.')
    dividend_method = st.radio('Dividend input method', ['Direct dividend', 'EPS × payout'])
    if dividend_method == 'EPS × payout':
        eps = st.number_input(f'Annual EPS ({currency}) — your assumption', min_value=0.0, value=7.0 if apple else 25.0, step=0.1)
        assumed_payout = st.slider('Assumed dividend payout (%)', 0, 100, 15 if apple else 40)
        d0 = eps * assumed_payout / 100
        st.caption(f'Model D₀ = {currency}{d0:.4f}. EPS is illustrative; this replaces the direct dividend input, except in Multistage.')
    st.caption('Initial growth 15%, stable growth 5%, return 10% are learning assumptions, not analyst forecasts.')

st.caption(f'Active D₀ = {currency}{d0:.4f} • Required return = {r:.1%} • Stable growth = {stable:.1%} • Comparison price = {currency}{price:.2f}')

try:
    custom = [float(x.strip()) for x in raw.split(',')]
    if not custom or len(custom) > 50 or any(not math.isfinite(x) or x < 0 for x in custom):
        raise ValueError()
except ValueError:
    st.error('Enter 1–50 finite, non-negative annual dividend amounts separated by commas.')
    st.stop()

models = ['Zero growth', 'Gordon growth', 'Two stage', 'H-model', 'Three stage', 'Multistage']
notes = {
'Zero growth': ('A fixed dividend forever, similar to a perpetual fixed preferred dividend.', r'V_0 = D/r', 'The next dividend equals the latest dividend. Growth is zero; the stable-growth input is ignored.'),
'Gordon growth': ('A mature company with sustainable constant dividend growth.', r'V_0 = D_1/(r-g),\quad D_1=D_0(1+g)', 'Use next year’s dividend in the numerator. A high short-term growth rate should not automatically be assumed forever.'),
'Two stage': ('A company with an initial growth phase followed by an abrupt change to stable growth.', r'V_0=\sum_{t=1}^{N}\frac{D_t}{(1+r)^t}+\frac{D_{N+1}}{(r-g)(1+r)^N}', 'Terminal value is measured at the END of year N, using dividend N+1. Discount it N years.'),
'H-model': ('An approximation for growth fading linearly from an initial rate to a stable rate.', r'V_0=\frac{D_0(1+g_L)+D_0H(g_S-g_L)}{r-g_L},\quad H=N/2', 'H is half the transition duration. This formula is an approximation; it is not an exact annual cash-flow valuation.'),
'Three stage': ('A growth phase, a transition phase and a perpetual stable phase.', r'V_0=\sum_{t=1}^{N+M}\frac{D_t}{(1+r)^t}+\frac{D_{N+M+1}}{(r-g)(1+r)^{N+M}}', 'Linear fade starts below initial growth in the first transition year and reaches stable growth in the final transition year. A constant middle-growth option is also provided.'),
'Multistage': ('A company requiring an individual forecast for each annual dividend.', r'V_0=\sum_{t=1}^{N}\frac{D_t}{(1+r)^t}+\frac{D_N(1+g)}{(r-g)(1+r)^N}', 'You enter dividend amounts directly. Zero dividends are allowed during the explicit period; a final zero dividend implies zero terminal value under this model.')}

results = {}
for model, tab in zip(models, st.tabs(models)):
    with tab:
        description, formula, caution = notes[model]
        st.subheader(model)
        st.write(description)
        st.latex(formula)
        st.caption(caution)
        if model != 'Zero growth' and r <= stable:
            st.error('Required return must exceed perpetual stable growth: r > g. This perpetuity formula is invalid otherwise.')
            continue
        value, rows, tv, pvtv = value_for(model, d0, high, stable, n, m, middle, transition, custom, r)
        results[model] = value
        c1, c2, c3 = st.columns(3)
        c1.metric('Estimated value per share', f'{currency}{value:,.2f}')
        c2.metric('Current share price', f'{currency}{price:,.2f}')
        gap = (value / price - 1) * 100
        c3.metric('Value relative to price', f'{gap:+.1f}%')
        st.write('Under these assumptions, estimated value is ' + ('above' if gap > 0 else 'below' if gap < 0 else 'equal to') + ' the market price. This is a model result, not a trading recommendation.')
        st.caption(f'Implied total equity value = {currency}{value * shares:,.2f} billion (value per share × {shares:g} billion shares).')
        with st.expander('Follow the calculation', expanded=True):
            if rows:
                frame = pd.DataFrame(rows).set_index('Year')
                st.dataframe(frame.style.format({c: '{:,.4f}' for c in frame.columns}), use_container_width=True)
                st.caption('Growth rates in the table are decimals: 0.15 means 15%.')
                st.write(f'1. PV of explicit dividends = {currency}{sum(x["PV dividend"] for x in rows):,.2f}')
                st.write(f'2. Terminal value at end of year {len(rows)} = {currency}{tv:,.2f}')
                st.write(f'3. PV of terminal value = {currency}{pvtv:,.2f}')
                st.write(f'4. Add steps 1 and 3 = {currency}{value:,.2f}')
                st.line_chart(frame[['Dividend']], use_container_width=True)
                if value > 0:
                    st.caption(f'Terminal value contributes {pvtv/value:.1%} of total value. A large contribution means long-term assumptions strongly influence the result.')
                st.download_button('Download cash-flow workpaper', frame.to_csv().encode(), f'{model.lower().replace(" ", "-")}.csv', key='download_'+model)
            elif model == 'Zero growth':
                st.write(f'{currency}{d0:,.2f} ÷ {r:.2%} = {currency}{value:,.2f}')
            elif model == 'Gordon growth':
                st.write(f'D₁ = {currency}{d0:,.2f} × (1 + {stable:.2%}) = {currency}{d0*(1+stable):,.2f}')
                st.write(f'Value = {currency}{d0*(1+stable):,.2f} ÷ ({r:.2%} − {stable:.2%}) = {currency}{value:,.2f}')
                st.write(f'Implied return at current price = D₁ / P₀ + g = {d0*(1+stable)/price+stable:.2%}')
            else:
                base = d0*(1+stable)/(r-stable)
                extra = d0*(n/2)*(high-stable)/(r-stable)
                st.write(f'H = {n}/2 = {n/2:g} years')
                st.write(f'Stable-growth component = {currency}{base:,.2f}; excess-growth component = {currency}{extra:,.2f}')
                exact, comparison, _, _ = forecast(d0, [high+(stable-high)*(j+1)/n for j in range(n)], r, stable)
                st.write(f'Exact annual fade illustration = {currency}{exact:,.2f}; H-model approximation = {currency}{value:,.2f}')
                st.caption('The annual illustration steps growth down each year and reaches stable growth in year N. It is a discrete convention, not an exact replication of continuous linear fading.')
                st.line_chart(pd.DataFrame(comparison).set_index('Year')[['Dividend']])
        with st.expander('Sensitivity: required return versus stable growth'):
            rr = [r + delta / 100 for delta in [-2, -1, 0, 1, 2] if r + delta / 100 > 0]
            gg = [stable + delta / 100 for delta in [-2, -1, 0, 1, 2]]
            table = {}
            for g in gg:
                table[f'g {g:.1%}'] = [None if model != 'Zero growth' and rate <= g else value_for(model, d0, high, g, n, m, middle, transition, custom, rate)[0] for rate in rr]
            st.dataframe(pd.DataFrame(table, index=[f'r {x:.1%}' for x in rr]).style.format(currency + '{:,.2f}', na_rep='Invalid'), use_container_width=True)
            if model == 'Zero growth':
                st.caption('All columns match because this model ignores growth.')

st.divider()
st.subheader('Compare the assumptions, not just the answers')
if results:
    st.bar_chart(pd.DataFrame({f'Value per share ({currency})': results}))
st.caption('Models share sidebar inputs, but their growth paths differ. Multistage uses your separate explicit dividend forecasts. H-model uses an approximation.')
if results:
    st.subheader('Save and compare your experiments')
    st.caption('Save several assumption sets during this session; download the comparison to keep it after a restart.')
    scenario_name = st.text_input('Scenario name', 'My Apple base case' if apple else 'My base case')
    saved = st.session_state.setdefault('saved_scenarios', [])
    if st.button('Save current scenario'):
        saved.append({'Scenario': scenario_name, 'Company': company, 'Currency': currency,
                      'Dividend basis': basis, 'Input method': dividend_method,
                      'D0': d0, 'Price': price, 'Shares (bn)': shares,
                      'Return (%)': r*100, 'Stable growth (%)': stable*100,
                      'Initial growth (%)': high*100, 'Initial years': n,
                      'Transition years': m, 'Transition': transition,
                      'Middle growth (%)': middle*100, 'Explicit dividends': raw,
                      **{f'{k} value/share': v for k, v in results.items()}})
    if saved:
        comparison = pd.DataFrame(saved)
        st.dataframe(comparison, use_container_width=True)
        st.download_button('Download scenario comparison', comparison.to_csv(index=False).encode(),
                           'equity-scenarios.csv', 'text/csv')
        if st.button('Clear saved scenarios'):
            saved.clear()
            st.rerun()
    assumptions = {'company': company, 'currency': currency, 'snapshot_date': '2026-10-25',
                   'dividend_basis': basis, 'input_method': dividend_method, 'D0': d0,
                   'comparison_price': price, 'shares_billions': shares, 'required_return': r,
                   'stable_growth': stable, 'initial_growth': high, 'initial_years': n,
                   'transition_years': m, 'transition': transition, 'middle_growth': middle,
                   'explicit_dividends': custom, 'values_per_share': results}
    st.download_button('Download current assumptions and values', json.dumps(assumptions, indent=2),
                       'equity-assumptions.json', 'application/json')
    if apple:
        st.write('Experiment: compare $1.08 annual dividends with a higher EPS × payout dividend. Then raise the required return from 10% to 12%. Explain why the valuation changes before looking at the answer.')
        st.caption('Changing payout here changes the dividend base; it does not automatically change growth. For a consistent earnings-driven forecast, reassess reinvestment, growth and payout together. Buybacks are not added to dividends in this module.')
with st.expander('Growth fundamentals: retention × ROE'):
    roe = st.number_input('Return on equity (%)', 0.0, 100.0, 15.0)
    payout = st.slider('Dividend payout ratio (%)', 0, 100, 40)
    sustainable = (1-payout/100)*roe
    st.metric('Sustainable growth estimate', f'{sustainable:.2f}%')
    st.write(f'Retention = {100-payout}%; growth = retention × ROE = {sustainable:.2f}%.')
    st.caption('Assumes stable ROE and retention with no new external equity. This is a learning calculation; it does not automatically replace stable growth above.')
with st.expander('Try this experiment'):
    st.write('Set D₀ = ₹10, r = 10% and g = 5%. Gordon value should be ₹210. Increase r to 12%: value falls to ₹150. Explain why before changing the input.')
    st.write('Next compare two-stage and H-model values. Both start from the same initial growth input, but only one maintains it throughout the initial stage.')
st.markdown('[Model reference: CFA Institute — Discounted Dividend Valuation](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/discounted-dividend-valuation)')
st.caption('Independent study aid. Not affiliated with or endorsed by CFA Institute. Refreshing the page may reset inputs; export workpapers to retain your calculations.')
