import math
import pandas as pd
import streamlit as st

st.set_page_config(page_title='Apple dividend case study', page_icon='🍎', layout='wide')

# Payment dates and amounts from Apple Investor Relations. All observations are
# after the August 2020 split; no split adjustment is required for this window.
PAYMENTS = [
('2021-02-11',.205),('2021-05-13',.22),('2021-08-12',.22),('2021-11-11',.22),
('2022-02-10',.22),('2022-05-12',.23),('2022-08-11',.23),('2022-11-10',.23),
('2023-02-16',.23),('2023-05-18',.24),('2023-08-17',.24),('2023-11-16',.24),
('2024-02-15',.24),('2024-05-16',.25),('2024-08-15',.25),('2024-11-14',.25),
('2025-02-13',.25),('2025-05-15',.26),('2025-08-14',.26),('2025-11-13',.26),
('2026-02-12',.26),('2026-05-14',.27),('2026-08-13',.27)]


def annual_history():
    df = pd.DataFrame(PAYMENTS, columns=['Payment date','Dividend (USD/share)'])
    df['Payment date'] = pd.to_datetime(df['Payment date'])
    df['Calendar year'] = df['Payment date'].dt.year
    annual = df.groupby('Calendar year')['Dividend (USD/share)'].agg(['sum','count'])
    return df, annual


def ddm(model, d0, r, g, high, n, m, middle, fade, custom):
    if model == 'Zero growth':
        return d0/r, [], None, None
    if model == 'Gordon growth':
        return d0*(1+g)/(r-g), [], None, None
    if model == 'H-model':
        return d0*((1+g)+n/2*(high-g))/(r-g), [], None, None
    if model == 'Multistage':
        dividends = custom
    else:
        rates = [high]*n
        if model == 'Three stage':
            rates += [high+(g-high)*(i+1)/m for i in range(m)] if fade else [middle]*m
        dividends = []
        d = d0
        for growth in rates:
            d *= 1+growth
            dividends.append(d)
    rows = [{'Year':i,'Dividend (USD)':d,'PV dividend (USD)':d/(1+r)**i}
            for i,d in enumerate(dividends,1)]
    terminal = dividends[-1]*(1+g)/(r-g)
    pvterminal = terminal/(1+r)**len(dividends)
    return sum(x['PV dividend (USD)'] for x in rows)+pvterminal,rows,terminal,pvterminal


st.title('🍎 Apple: from real dividends to a valuation')
st.caption('AAPL • USD per share • Verified snapshot: 23 October 2026 • No live market feed')
st.markdown('[Dividend data: Apple Investor Relations](https://investor.apple.com/dividend-history/)')
st.write('Start with observed dividends. Then choose your own future assumptions and compare the DDM models.')
df, annual = annual_history()
complete = annual[annual['count']==4]
cagr = (complete.loc[2025,'sum']/complete.loc[2021,'sum'])**(1/4)-1
last = PAYMENTS[-1][1]
ttm = sum(x[1] for x in PAYMENTS[-4:])
a,b,c = st.columns(3)
a.metric('Latest paid quarterly dividend',f'${last:.2f}')
b.metric('Last four payments: trailing annual dividend',f'${ttm:.2f}')
c.metric('Latest quarter × 4: annualized run rate',f'${last*4:.2f}')
st.caption('Latest included payment: 13 August 2026. Trailing total is actual payments; run rate assumes four quarters at the latest rate and is not a declared annual dividend.')
history, valuation, learning = st.tabs(['1 · Actual history','2 · Model Apple','3 · Understand the result'])
with history:
    display = annual.rename(columns={'sum':'Dividend total (USD/share)','count':'Payments included'}).copy()
    display['Period'] = ['Complete calendar year' if y<2026 else '2026 YTD through 23 Oct' for y in display.index]
    display['YoY growth (complete years only)'] = complete['sum'].pct_change()
    st.dataframe(display.style.format({'Dividend total (USD/share)':'${:.3f}','YoY growth (complete years only)':'{:.2%}'},na_rep='—'),use_container_width=True)
    st.bar_chart(complete[['sum']].rename(columns={'sum':'Annual dividend (USD/share)'}))
    st.caption('Chart excludes incomplete 2026. These are calendar-year totals, not Apple fiscal-year totals. All payments are after the 2020 split.')
    st.metric('2021–2025 dividend CAGR: four annual intervals',f'{cagr:.2%}')
    st.latex(r'g_{historical}=(D_{2025}/D_{2021})^{1/4}-1')
    st.write(f'(${complete.loc[2025,"sum"]:.3f} / ${complete.loc[2021,"sum"]:.3f})^(1/4) − 1 = {cagr:.2%}.')
    st.write(f'Latest quarterly rate increase: $0.26 → $0.27 = {(0.27/0.26-1):.2%}. This differs from annual-total growth because the increase occurs partway through the year.')
    with st.expander('Every included payment'):
        st.dataframe(df[['Payment date','Dividend (USD/share)']],use_container_width=True,hide_index=True)
    st.download_button('Download verified payment history',df.to_csv(index=False).encode(),'apple_dividends_snapshot_2026-10-23.csv')
with valuation:
    st.info('Actual dividend inputs are sourced. Required return, future growth and stage lengths are your assumptions—not Apple guidance or analyst forecasts.')
    basis = st.selectbox('Annual D₀ basis',['Trailing four payments','Latest quarterly rate × 4','Last complete calendar year (2025)'])
    base = {'Trailing four payments':ttm,'Latest quarterly rate × 4':last*4,'Last complete calendar year (2025)':float(complete.loc[2025,'sum'])}[basis]
    st.write(f'Selected annual D₀ = **${base:.3f} per share**.')
    col1,col2 = st.columns(2)
    with col1:
        r = st.number_input('Required annual equity return (%)',min_value=.1,max_value=100.,value=10.,step=.5)/100
        choice = st.selectbox('Stable-growth starting assumption',['My own estimate','Historical 2021–2025 CAGR (illustration)'])
        g = st.number_input('My perpetual growth estimate (%)',min_value=-50.,max_value=50.,value=3.,step=.5)/100 if choice=='My own estimate' else cagr
        if choice!='My own estimate':
            st.warning(f'Using {cagr:.2%} historical growth as a future assumption for illustration. Past growth does not establish a sustainable perpetual rate.')
        high = st.number_input('Initial annual growth assumption (%)',min_value=-50.,max_value=100.,value=6.,step=.5)/100
        n = st.slider('Initial stage / H-model transition years',1,20,5)
    with col2:
        m = st.slider('Three-stage middle years',1,15,5)
        fade = st.selectbox('Middle-stage pattern',['Linear fade','Constant middle growth'])=='Linear fade'
        middle = st.number_input('Constant middle growth (%)',min_value=-50.,max_value=100.,value=4.)/100
        raw = st.text_input('Multistage: your annual dividend forecasts ($)','1.10, 1.16, 1.22, 1.28, 1.34')
        price = st.number_input('Optional observed share price ($; 0 = skip)',min_value=0.,value=0.,step=1.)
        price_date = st.date_input('Price observation date (only if entering a price)')
    st.caption('Annual end-of-year dividend approximation; Apple actually pays quarterly. Multistage uses your explicit amounts instead of annual D₀. No price is fetched or invented.')
    try:
        custom = [float(x.strip()) for x in raw.split(',')]
        if not custom or len(custom)>50 or any(not math.isfinite(x) or x<0 for x in custom):raise ValueError()
    except ValueError:
        st.error('Use 1–50 finite non-negative dividend amounts separated by commas.');st.stop()
    if r<=g:
        st.error('For growing perpetuities, required return must exceed stable growth (r > g). Lower g or increase r.');st.stop()
    names=['Zero growth','Gordon growth','Two stage','H-model','Three stage','Multistage']
    results={name:ddm(name,base,r,g,high,n,m,middle,fade,custom) for name in names}
    summary=pd.DataFrame({'Estimated value ($/share)':{k:v[0] for k,v in results.items()}})
    if price>0:
        summary['Value relative to entered price (%)']=(summary.iloc[:,0]/price-1)*100
        st.caption(f'Comparison uses your entered price ${price:.2f}, dated {price_date}; it is not a live quote.')
    st.dataframe(summary.style.format('{:,.2f}'),use_container_width=True)
    selected=st.selectbox('Inspect a model',names,index=1)
    value,rows,tv,pvtv=results[selected]
    st.metric('Selected model value',f'${value:,.2f}')
    if rows:
        frame=pd.DataFrame(rows).set_index('Year')
        st.dataframe(frame.style.format('{:,.4f}'),use_container_width=True)
        st.line_chart(frame[['Dividend (USD)']])
        st.write(f'PV explicit dividends = ${sum(x["PV dividend (USD)"] for x in rows):.2f}; terminal value at year {len(rows)} = ${tv:.2f}; PV terminal value = ${pvtv:.2f}.')
        st.write(f'Value = PV dividends + PV terminal value = ${value:.2f}.')
        st.download_button('Download selected model cash flows',frame.to_csv().encode(),'apple_ddm_workpaper.csv')
    elif selected=='Gordon growth':
        st.latex(r'V_0=D_0(1+g)/(r-g)')
        st.write(f'D₁ = ${base:.3f} × (1 + {g:.2%}) = ${base*(1+g):.4f}. Divide by ({r:.2%} − {g:.2%}) to get ${value:.2f}.')
        if price>0:st.write(f'Gordon implied return at entered price = D₁/P₀ + g = {base*(1+g)/price+g:.2%}.')
    elif selected=='Zero growth':
        st.write(f'${base:.3f} / {r:.2%} = ${value:.2f}. Stable growth is ignored.')
    else:
        st.latex(r'V_0=[D_0(1+g_L)+D_0H(g_S-g_L)]/(r-g_L),\quad H=N/2')
        st.write(f'H = {n/2:g}. This is the H-model approximation, not an exact annual cash-flow calculation.')
    st.subheader('Sensitivity: Gordon value ($/share)')
    rr=[r+x/100 for x in [-2,-1,0,1,2] if r+x/100>0]
    gg=[g+x/100 for x in [-2,-1,0,1,2]]
    sensitivity=pd.DataFrame({f'g {growth:.1%}':[base*(1+growth)/(rate-growth) if rate>growth else None for rate in rr] for growth in gg},index=[f'r {rate:.1%}' for rate in rr])
    st.dataframe(sensitivity.style.format('${:.2f}',na_rep='Invalid'),use_container_width=True)
with learning:
    st.subheader('Does a low DDM estimate mean Apple is cheap or expensive?')
    st.write('A dividend-only result depends on the payout policy you forecast. Apple also returns capital through share repurchases. A model that simply extends today’s cash dividend can omit important future distributions or changes in payout policy. A gap to the share price is a reason to inspect assumptions and model suitability—not a stand-alone investment conclusion.')
    st.markdown('[Apple’s April 2026 release: dividend and repurchase authorization](https://www.apple.com/in/newsroom/2026/04/apple-reports-second-quarter-results/)')
    st.write('An authorization is permission to repurchase shares, not evidence that the full amount was spent. Do not add the authorized amount directly to dividends.')
    st.write('Try: compare trailing dividends with the annualized run rate; then raise required return by two percentage points. Finally test whether extrapolating historical growth forever is a reasonable business assumption.')
    st.caption('Potential next comparison: FCFE or a carefully specified total-payout model. Buybacks can affect per-share forecasts, so avoid double counting them.')
st.caption('Static source snapshot, not automatic updates. All valuations are educational scenarios. Inputs reset on reload; export tables to keep your work.')
