import math
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
st.info('Fictional company • Annual dividends per share • End-of-year payments • Constant required return • Learning tool')
with st.sidebar:
    st.header('Company assumptions')
    d0 = st.number_input('Latest dividend D₀ (₹ per share)', min_value=0.0, value=10.0, step=1.0)
    price = st.number_input('Current share price (₹)', min_value=0.01, value=200.0, step=10.0)
    r = st.number_input('Required return r (%)', min_value=0.1, max_value=100.0, value=10.0, step=0.5) / 100
    stable = st.number_input('Stable growth g (%)', min_value=-50.0, max_value=50.0, value=5.0, step=0.5) / 100
    high = st.number_input('Initial growth (%)', min_value=-50.0, max_value=100.0, value=15.0, step=1.0) / 100
    n = st.slider('Initial stage / H-model fade years', 1, 20, 5)
    m = st.slider('Three-stage transition years', 1, 15, 5)
    transition = st.selectbox('Three-stage transition', ['Linear fade', 'Constant middle growth'])
    middle = st.number_input('Middle-stage growth (%)', min_value=-50.0, max_value=100.0, value=8.0) / 100
    raw = st.text_input('Multistage: annual dividend forecasts (₹)', '10, 12, 15, 17, 18')
    st.caption('Comma-separated amounts D₁ … Dₙ, not growth rates. These override D₀ in the multistage model.')

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
        c1.metric('Estimated value per share', f'₹{value:,.2f}')
        c2.metric('Current share price', f'₹{price:,.2f}')
        gap = (value / price - 1) * 100
        c3.metric('Value relative to price', f'{gap:+.1f}%')
        st.write('Under these assumptions, estimated value is ' + ('above' if gap > 0 else 'below' if gap < 0 else 'equal to') + ' the market price. This is a model result, not a trading recommendation.')
        with st.expander('Follow the calculation', expanded=True):
            if rows:
                frame = pd.DataFrame(rows).set_index('Year')
                st.dataframe(frame.style.format({c: '{:,.4f}' for c in frame.columns}), use_container_width=True)
                st.caption('Growth rates in the table are decimals: 0.15 means 15%.')
                st.write(f'1. PV of explicit dividends = ₹{sum(x["PV dividend"] for x in rows):,.2f}')
                st.write(f'2. Terminal value at end of year {len(rows)} = ₹{tv:,.2f}')
                st.write(f'3. PV of terminal value = ₹{pvtv:,.2f}')
                st.write(f'4. Add steps 1 and 3 = ₹{value:,.2f}')
                st.line_chart(frame[['Dividend']], use_container_width=True)
                if value > 0:
                    st.caption(f'Terminal value contributes {pvtv/value:.1%} of total value. A large contribution means long-term assumptions strongly influence the result.')
                st.download_button('Download cash-flow workpaper', frame.to_csv().encode(), f'{model.lower().replace(" ", "-")}.csv', key='download_'+model)
            elif model == 'Zero growth':
                st.write(f'₹{d0:,.2f} ÷ {r:.2%} = ₹{value:,.2f}')
            elif model == 'Gordon growth':
                st.write(f'D₁ = ₹{d0:,.2f} × (1 + {stable:.2%}) = ₹{d0*(1+stable):,.2f}')
                st.write(f'Value = ₹{d0*(1+stable):,.2f} ÷ ({r:.2%} − {stable:.2%}) = ₹{value:,.2f}')
                st.write(f'Implied return at current price = D₁ / P₀ + g = {d0*(1+stable)/price+stable:.2%}')
            else:
                base = d0*(1+stable)/(r-stable)
                extra = d0*(n/2)*(high-stable)/(r-stable)
                st.write(f'H = {n}/2 = {n/2:g} years')
                st.write(f'Stable-growth component = ₹{base:,.2f}; excess-growth component = ₹{extra:,.2f}')
                exact, comparison, _, _ = forecast(d0, [high+(stable-high)*(j+1)/n for j in range(n)], r, stable)
                st.write(f'Exact annual fade illustration = ₹{exact:,.2f}; H-model approximation = ₹{value:,.2f}')
                st.caption('The annual illustration steps growth down each year and reaches stable growth in year N. It is a discrete convention, not an exact replication of continuous linear fading.')
                st.line_chart(pd.DataFrame(comparison).set_index('Year')[['Dividend']])
        with st.expander('Sensitivity: required return versus stable growth'):
            rr = [r + delta / 100 for delta in [-2, -1, 0, 1, 2] if r + delta / 100 > 0]
            gg = [stable + delta / 100 for delta in [-2, -1, 0, 1, 2]]
            table = {}
            for g in gg:
                table[f'g {g:.1%}'] = [None if model != 'Zero growth' and rate <= g else value_for(model, d0, high, g, n, m, middle, transition, custom, rate)[0] for rate in rr]
            st.dataframe(pd.DataFrame(table, index=[f'r {x:.1%}' for x in rr]).style.format('₹{:,.2f}', na_rep='Invalid'), use_container_width=True)
            if model == 'Zero growth':
                st.caption('All columns match because this model ignores growth.')

st.divider()
st.subheader('Compare the assumptions, not just the answers')
if results:
    st.bar_chart(pd.DataFrame({'Value per share (₹)': results}))
st.caption('Models share sidebar inputs, but their growth paths differ. Multistage uses your separate explicit dividend forecasts. H-model uses an approximation.')
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
