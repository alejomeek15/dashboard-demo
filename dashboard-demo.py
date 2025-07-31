import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- INITIAL CONFIGURATION ---
st.set_page_config(
    page_title="Strategic Sales Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS STYLES ---
st.markdown("""
<style>
    /* Style for Streamlit's standard metrics */
    .stMetric {
        border-radius: 10px;
        background-color: #f0f2f6;
        padding: 15px;
    }
    .stMetric-value {
        font-size: 2em;
    }
    /* Styles for our custom KPI cards */
    .custom-metric {
        border-radius: 10px;
        background-color: #f0f2f6;
        padding: 15px;
        text-align: left;
        height: 100%;
    }
    .metric-label {
        font-size: 1rem;
        color: #555;
        margin-bottom: 8px;
    }
    .metric-value-main {
        font-size: 2em;
        font-weight: 600;
        line-height: 1.2;
    }
    .metric-value-comp {
        font-size: 0.9rem;
        color: #888;
        margin-bottom: 8px;
    }
    .metric-delta {
        font-size: 1rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


# --- HELPER FUNCTIONS ---
@st.cache_data
def load_data_from_gsheets(sheet_id):
    """Loads data from a public Google Sheet for the demo."""
    try:
        # Construct the URL to export the sheet as CSV.
        # The demo sheet is named 'Sales'.
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&sheet=Sales"
        df = pd.read_csv(url)
        
        # Process the new columns: 'date', 'store', 'sales'
        df['date'] = pd.to_datetime(df['date'])
        df['sales'] = pd.to_numeric(df['sales'])

        # Create new date-related columns in English for filtering and analysis
        df['year'] = df['date'].dt.year
        df['month_num'] = df['date'].dt.month
        df['day_of_week'] = df['date'].dt.day_name()
        df['month_name'] = df['date'].dt.strftime('%b') # Short month name (e.g., Jan)
        df['month_year'] = df['date'].dt.to_period('M').astype(str)
        
        return df
    except Exception as e:
        st.error(f"Error loading data from Google Sheets: {e}")
        st.info("Please ensure the Google Sheet is public ('Anyone with the link can view') and the tab is named 'Sales'.")
        return None


def create_heatmap(df, title):
    """Creates a Plotly heatmap figure."""
    if df.empty:
        st.info(f"No data available to generate heatmap: {title}")
        return None
    
    ordered_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    heatmap_data = df.pivot_table(
        values='sales', index='store', columns='day_of_week', aggfunc='mean'
    ).reindex(columns=ordered_days)
    
    fig = px.imshow(
        heatmap_data,
        labels=dict(x="Day of Week", y="Store", color="Average Sales"),
        x=ordered_days, y=heatmap_data.index,
        text_auto=".2s", aspect="auto", color_continuous_scale="Viridis",
        title=title
    )
    fig.update_xaxes(side="top")
    return fig

def create_stats_barchart(df, title):
    """Creates a bar chart for mean and median sales per store."""
    if df.empty:
        st.info(f"No data available to generate stats chart: {title}")
        return None
        
    df_operating_days = df[df['sales'] > 0]
    
    stats = df_operating_days.groupby('store')['sales'].agg(['mean', 'median']).reset_index()
    stats = stats.melt(id_vars='store', value_vars=['mean', 'median'], var_name='Metric', value_name='Value')
    
    fig = px.bar(
        stats,
        y='store',
        x='Value',
        color='Metric',
        barmode='group',
        orientation='h',
        title=title,
        labels={'Value': 'Daily Sales ($)', 'store': 'Store', 'Metric': 'Metric'},
        template='plotly_white',
        color_discrete_map={'mean': '#636EFA', 'median': '#FFA15A'},
        text='Value'
    )
    fig.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
    fig.update_layout(
        yaxis={'categoryorder':'total ascending'},
        uniformtext_minsize=8, 
        uniformtext_mode='hide'
    )
    return fig


# --- DATA LOADING ---
# The Google Sheet ID for your public demo data
sheet_id = "1kuzTBPdCy-42EWyIAjHP_Fi6klavRA7PyjoEfbuxCC0"
df_original = load_data_from_gsheets(sheet_id)

if df_original is None:
    st.stop()

# --- SIDEBAR WITH FILTERS ---
st.sidebar.title("🚀 Global Filters")
st.sidebar.markdown("Adjust the filters to explore the dashboard.")

compare_mode = st.sidebar.checkbox("Compare two periods", value=False)

st.sidebar.header("Main Period")
min_date = df_original['date'].min().to_pydatetime()
max_date = df_original['date'].max().to_pydatetime()

default_start_date = (max_date - pd.DateOffset(months=6)).date()
if default_start_date < min_date.date():
    start_value = min_date
else:
    start_value = default_start_date

start_date_1, end_date_1 = st.sidebar.date_input(
    "Select the date range:",
    value=(start_value, max_date),
    min_value=min_date,
    max_value=max_date,
    key="period1"
)

df_period_1 = df_original[
    (df_original['date'].between(pd.to_datetime(start_date_1), pd.to_datetime(end_date_1)))
]

df_period_2 = pd.DataFrame()
if compare_mode:
    st.sidebar.header("Comparison Period")
    default_start_2 = start_date_1 - pd.DateOffset(years=1)
    default_end_2 = end_date_1 - pd.DateOffset(years=1)

    start_date_2, end_date_2 = st.sidebar.date_input(
        "Select the comparison date range:",
        value=(default_start_2, default_end_2),
        min_value=min_date,
        max_value=max_date,
        key="period2"
    )
    df_period_2 = df_original[
        (df_original['date'].between(pd.to_datetime(start_date_2), pd.to_datetime(end_date_2)))
    ]

st.sidebar.header("Store Filter")
all_stores = sorted(df_original['store'].unique())
selected_stores = st.sidebar.multiselect(
    "Select stores:", options=all_stores, default=all_stores
)

df_period_1 = df_period_1[df_period_1['store'].isin(selected_stores)]
if not df_period_2.empty:
    df_period_2 = df_period_2[df_period_2['store'].isin(selected_stores)]

if df_period_1.empty:
    st.warning("No data available for the selected filters in the main period.")
    st.stop()

# --- MAIN SCREEN ---
st.title("🚀 Strategic Sales Dashboard")

tab1, tab2, tab3 = st.tabs(["📊 Executive Summary", "📈 Comparative Analysis", "📋 Data Explorer"])

with tab1:
    st.header("Business Overview")
    
    total_sales_1 = df_period_1['sales'].sum()
    avg_daily_sales_1 = df_period_1.groupby('date')['sales'].sum().mean()

    if compare_mode and not df_period_2.empty:
        total_sales_2 = df_period_2['sales'].sum()
        avg_daily_sales_2 = df_period_2.groupby('date')['sales'].sum().mean()
        sales_var = ((total_sales_1 - total_sales_2) / total_sales_2) * 100 if total_sales_2 > 0 else float('inf')
        avg_sales_var = ((avg_daily_sales_1 - avg_daily_sales_2) / avg_daily_sales_2) * 100 if avg_daily_sales_2 > 0 else float('inf')

        st.subheader("KPI Comparison")
        col1, col2 = st.columns(2)
        with col1:
            delta_color = "green" if sales_var >= 0 else "red"
            arrow = '▲' if sales_var >= 0 else '▼'
            html_kpi_1 = f"""
            <div class="custom-metric">
                <div class="metric-label">Total Sales</div>
                <div class="metric-value-main">${total_sales_1:,.0f}</div>
                <div class="metric-value-comp">vs. ${total_sales_2:,.0f} (comp.)</div>
                <div class="metric-delta" style="color:{delta_color};">
                    {arrow} {sales_var:.2f}%
                </div>
            </div>
            """
            st.markdown(html_kpi_1, unsafe_allow_html=True)
            
        with col2:
            delta_color = "green" if avg_sales_var >= 0 else "red"
            arrow = '▲' if avg_sales_var >= 0 else '▼'
            html_kpi_2 = f"""
            <div class="custom-metric">
                <div class="metric-label">Average Daily Sales</div>
                <div class="metric-value-main">${avg_daily_sales_1:,.0f}</div>
                <div class="metric-value-comp">vs. ${avg_daily_sales_2:,.0f} (comp.)</div>
                <div class="metric-delta" style="color:{delta_color};">
                    {arrow} {avg_sales_var:.2f}%
                </div>
            </div>
            """
            st.markdown(html_kpi_2, unsafe_allow_html=True)

    else:
        st.subheader("Main Period KPIs")
        col1, col2 = st.columns(2)
        col1.metric("Total Sales", f"${total_sales_1:,.0f}")
        col2.metric("Average Daily Sales", f"${avg_daily_sales_1:,.0f}")

    st.markdown("---")
    
    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.subheader("Monthly Sales Trend")
        
        if compare_mode and not df_period_2.empty:
            monthly_sales_1 = df_period_1.groupby(['month_num', 'month_name'])['sales'].sum().reset_index()
            monthly_sales_1['Period'] = 'Main'
            
            monthly_sales_2 = df_period_2.groupby(['month_num', 'month_name'])['sales'].sum().reset_index()
            monthly_sales_2['Period'] = 'Comparison'
            
            plot_df = pd.concat([monthly_sales_1, monthly_sales_2]).sort_values('month_num')
            
            fig_line = px.line(
                plot_df, x='month_name', y='sales', color='Period',
                title="Monthly Sales Comparison", labels={'sales': 'Sales ($)', 'month_name': 'Month'},
                markers=True, template='plotly_white',
                color_discrete_map={'Main': '#1f77b4', 'Comparison': '#ff7f0e'}
            )
        else:
            plot_df = df_period_1.groupby('month_year')['sales'].sum().reset_index()
            fig_line = px.line(
                plot_df, x='month_year', y='sales',
                title="Monthly Sales Evolution", labels={'sales': 'Sales ($)', 'month_year': 'Month'},
                markers=True, template='plotly_white'
            )

        fig_line.update_layout(xaxis_title=None, yaxis_title="Sales ($)", legend_title="Period")
        st.plotly_chart(fig_line, use_container_width=True)
        
    with col_b:
        st.subheader("Sales Composition by Store (Main Period)")
        store_sales = df_period_1.groupby('store')['sales'].sum().reset_index()
        fig_donut = px.pie(
            store_sales, names='store', values='sales',
            title="Sales Distribution", hole=0.4, template='plotly_white'
        )
        fig_donut.update_traces(textinfo='percent+label', textposition='inside')
        st.plotly_chart(fig_donut, use_container_width=True)

with tab2:
    st.header("Store Performance Analysis")
    st.subheader("Heatmap: Average Sales by Day of Week")

    if compare_mode and not df_period_2.empty:
        col1, col2 = st.columns(2)
        with col1:
            fig1 = create_heatmap(df_period_1, "Main Period")
            if fig1: st.plotly_chart(fig1, use_container_width=True)
        with col2:
            fig2 = create_heatmap(df_period_2, "Comparison Period")
            if fig2: st.plotly_chart(fig2, use_container_width=True)
    else:
        fig = create_heatmap(df_period_1, "Performance in Selected Period")
        if fig: st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    
    st.subheader("Typical Performance by Store (Mean & Median)")
    st.info("💡 The calculation of mean and median excludes days with zero sales for a fairer comparison of performance on operating days.")

    if compare_mode and not df_period_2.empty:
        col1, col2 = st.columns(2)
        with col1:
            fig_stats1 = create_stats_barchart(df_period_1, "Main Period")
            if fig_stats1: st.plotly_chart(fig_stats1, use_container_width=True)
        with col2:
            fig_stats2 = create_stats_barchart(df_period_2, "Comparison Period")
            if fig_stats2: st.plotly_chart(fig_stats2, use_container_width=True)
    else:
        fig_stats = create_stats_barchart(df_period_1, "Performance in Selected Period")
        if fig_stats: st.plotly_chart(fig_stats, use_container_width=True)


with tab3:
    st.header("Detailed Data Explorer")
    st.markdown("Data from the **main period**. You can sort and search.")
    
    df_display = df_period_1[['date', 'store', 'sales', 'day_of_week']].copy()
    df_display['sales'] = df_display['sales'].apply(lambda x: f"${x:,.0f}")
    df_display['date'] = df_display['date'].dt.strftime('%d/%m/%Y')
    
    st.dataframe(
        df_display.sort_values(by="date", ascending=False), 
        use_container_width=True, hide_index=True
    )
