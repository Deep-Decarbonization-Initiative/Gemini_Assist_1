import streamlit as st
import json
import pandas as pd
import numpy as np
import altair as alt
from pathlib import Path
import gc  # MEMORY OPTIMIZATION: Garbage Collection

# ==============================================================================
# HEADER SECTION
# ==============================================================================
st.title("D2I Subscription Experiment")
st.title("Spring 2026 🚗🔌⚡")
st.write(
    "Data below reflects all Level 2 PowerFlex and ChargePoint sessions associated with BEV drivers in the Offer, Gift, and Control groups in the SP26 experiment.  " \
    "It does not include any data from non-Triton Charger drivers, nor any data from Triton Chargers who were ineligible for the experiment.  "
    "Analagous comparisons for PHEV drivers in the experiment are available at: [Link TBD]."
)
"""
# Did the subscription experiment reshape EV charging behavior? 
All results below are preliminary and subject to change.  
The underlying datasets can be viewed below (but are hidden by default), followed by selectable options (e.g., timescale to view and groups of drivers to display) and then descriptive figures.
"""

# Approach 1 Paths: Split Outcomes and Characteristics
outcomes_path = Path('data/SP26_userxweek_charging_outcomes_bev_13jul26.parquet')
chars_path = Path('data/SP26_club_data_bev_13jul26.parquet')

# PERFORMANCE & MEMORY FIX: Cache, cap entries, and downcast split dataset numeric schemas
@st.cache_data(max_entries=1)  # MEMORY OPTIMIZATION: Prevent cache bloat
def load_split_data():
    df_outcomes = pd.read_parquet(outcomes_path) if outcomes_path.exists() else None
    df_chars = pd.read_parquet(chars_path) if chars_path.exists() else None
    
    # MEMORY OPTIMIZATION: Downcast numerical columns for both split dataframes
    if df_outcomes is not None:
        for col in df_outcomes.select_dtypes(include=['int64']).columns:
            df_outcomes[col] = pd.to_numeric(df_outcomes[col], downcast='integer')
        for col in df_outcomes.select_dtypes(include=['float64']).columns:
            df_outcomes[col] = pd.to_numeric(df_outcomes[col], downcast='float')
            
    if df_chars is not None:
        for col in df_chars.select_dtypes(include=['int64']).columns:
            df_chars[col] = pd.to_numeric(df_chars[col], downcast='integer')
        for col in df_chars.select_dtypes(include=['float64']).columns:
            df_chars[col] = pd.to_numeric(df_chars[col], downcast='float')
            
    return df_outcomes, df_chars

df_outcomes_raw, df_chars_raw = load_split_data()

if df_outcomes_raw is not None and df_chars_raw is not None:
    st.success("Loaded SP26 Outcomes and Characteristics datasets successfully!")
    df_outcomes = df_outcomes_raw.copy()
    df_chars = df_chars_raw.copy()
else:
    if df_outcomes_raw is None:
        st.warning(f"Outcomes file not found: {outcomes_path}")
    if df_chars_raw is None:
        st.warning(f"Characteristics file not found: {chars_path}")
    st.stop()

show_research_dataset = st.checkbox('Show SP26 Raw Datasets', value=False)
if show_research_dataset:
    st.write(f"Outcomes dataset contains {len(df_outcomes)} rows and {len(df_outcomes.columns)} columns.")
    st.write(f"Characteristics dataset contains {len(df_chars)} rows and {len(df_chars.columns)} columns.")
    st.write('Showing first 50 rows of Outcomes:')
    st.dataframe(df_outcomes.head(50))
    st.write('Showing first 50 rows of Characteristics:')
    st.dataframe(df_chars.head(50))

# Identify driver tracking ID column dynamically from the master characteristics table
driver_col_id = 'driver' if 'driver' in df_chars.columns else ('userid' if 'userid' in df_chars.columns else df_chars.columns[0])

if 'week' in df_outcomes.columns:
    df_outcomes['week'] = pd.to_numeric(df_outcomes['week'], errors='coerce')
    df_outcomes = df_outcomes.dropna(subset=['week'])
    df_outcomes['week'] = df_outcomes['week'].astype(int)

    # Identify the sessions metric column to sum up (successful_sessions)
    sessions_col = 'successful_sessions' if 'successful_sessions' in df_outcomes.columns else ('sessions' if 'sessions' in df_outcomes.columns else None)

    if not sessions_col:
        st.error("Could not find a valid sessions metric column (e.g., 'successful_sessions') in the dataset.")
        st.stop()

    # Process event markers directly from the weekly data structure
    if 'event' in df_outcomes.columns:
        df_outcomes['event'] = pd.to_numeric(df_outcomes['event'], errors='coerce')
    else:
        df_outcomes['event'] = np.nan

    if 'event_detail' in df_outcomes.columns:
        df_outcomes['event_detail'] = df_outcomes['event_detail'].astype(str)
    else:
        df_outcomes['event_detail'] = ''

    event_markers = df_outcomes[
        df_outcomes['event'].notna() & 
        (df_outcomes['event_detail'] != '') & 
        (df_outcomes['event_detail'] != 'nan')
    ].copy()

    if not event_markers.empty:
        event_markers = event_markers.drop_duplicates(subset=['week'])

    # Process UCSD holiday markers directly from the weekly data structure
    if 'ucsd_holiday' in df_outcomes.columns:
        df_outcomes['ucsd_holiday'] = pd.to_numeric(df_outcomes['ucsd_holiday'], errors='coerce').fillna(0)
    else:
        df_outcomes['ucsd_holiday'] = 0

    holiday_markers = df_outcomes[df_outcomes['ucsd_holiday'] > 0].copy()
    if not holiday_markers.empty:
        holiday_markers = holiday_markers.drop_duplicates(subset=['week'])

    # ==============================================================================
    # SETTINGS SECTION
    # ==============================================================================
    st.markdown("---")
    st.header('Configuration Settings 🛠️')
    """
   The following sections control what data is visualized and how it is disaggregated in the plots that follow.
   The timescale slider dynamically adjusts the timeframe on the figures. 
   The Inclusion Criteria section can be adjusted to exclude data associated with certain field values (e.g., a particular treatment group, or drivers who hadn't charged since any given academic year (AY)).
   The Disaggregation Fields then determine how to group the remaining data (e.g., by treatment group and/or given covariates).
   """
    
    """
   Reminder: drivetrain (PHEV vs BEV) is no longer an adjustable setting, as PHEV-related figures and data have been relocated to [Link TBD]
    """
    # --- Sub-section 1: Timescale ---
    st.subheader('1. Timescale 📅')
    
    data_min = int(df_outcomes['week'].min())
    data_max = int(df_outcomes['week'].max())
    
    slider_min = min(1, data_min)
    slider_max = max(185, data_max)
    
    selected_week_range = st.slider(
        "Select range of weeks to display below. These are indexed to January 1st, 2023. " \
        "For reference, the SP26 experimental offers went out during week 167, discounts began week 170, and discounts will end week 183:",
        min_value=slider_min,
        max_value=slider_max,
        value=(105, 183)
    )

    # Event Visibility Toggle Checkbox
    show_events = st.checkbox("Display event dates.", value=True)
    """
    Dotted vertical lines indicate significant events in the club's history, including key experiment dates. Solid background bars mark holiday weeks.
    """
    # --- Sub-section 2: Inclusion Criteria (Read entirely from df_chars) ---
    st.subheader('2. Inclusion Criteria: Treatment Groups and Covariates 🔍')
    """
    These options determine which driver-weeks pass the filtering rules to be used in final analytics.
    Note: The 'Offer' group is an aggregation of 'Paid', 'Ignored', and 'Left'.
    """
    # Mapping base tracking metrics explicitly to the characteristics dataset
    treatment_col = 'treatment' if 'treatment' in df_chars.columns else None
    recency_col = 'lastperiodcharged' if 'lastperiodcharged' in df_chars.columns else None
    energy_col = 'baselinekwhcharged' if 'baselinekwhcharged' in df_chars.columns else None
    freq_col = 'baselinedaysofcharging' if 'baselinedaysofcharging' in df_chars.columns else None
    loc_col = 'charginglocgroup' if 'charginglocgroup' in df_chars.columns else None
    bring_col = 'kwhcouldbringtocampus' if 'kwhcouldbringtocampus' in df_chars.columns else None

    # MINOR DATA QUIRK FIX: Helper function to clean 1.0 into 1 while leaving string categories alone
    def clean_int_str(s):
        def parse_val(x):
            if pd.isna(x): return x
            sx = str(x)
            if sx.replace('.', '', 1).isdigit():
                fx = float(sx)
                if fx.is_integer():
                    return str(int(fx))
            return sx
        return s.apply(parse_val)

    if energy_col: df_chars[energy_col] = clean_int_str(df_chars[energy_col])
    if freq_col: df_chars[freq_col] = clean_int_str(df_chars[freq_col])
    if bring_col: df_chars[bring_col] = clean_int_str(df_chars[bring_col])

    if treatment_col:
        if df_chars[treatment_col].dtype.name == 'category':
            df_chars[treatment_col] = df_chars[treatment_col].astype(str)
        unique_treatments = sorted(df_chars[treatment_col].dropna().astype(str).unique().tolist())
        
        offer_components = ['Paid', 'Ignored', 'Left']
        if any(comp in unique_treatments for comp in offer_components) and 'Offer' not in unique_treatments:
            unique_treatments.append('Offer')
            unique_treatments = sorted(unique_treatments)
            
        selected_treatments = st.multiselect("Treatment Group Filter (Note: Left refers to drivers who enrolled but did not pay):", options=unique_treatments, default=unique_treatments)
    else:
        selected_treatments = None

    if recency_col:
        unique_recencies = sorted(df_chars[recency_col].dropna().astype(str).unique().tolist())
        selected_recencies = st.multiselect("Charge Recency Filter (Academic year of most recent charge BEFORE experimental assignment):", options=unique_recencies, default=unique_recencies)
    else:
        selected_recencies = None

    if energy_col:
        unique_energies = sorted(df_chars[energy_col].dropna().astype(str).unique().tolist())
        selected_energies = st.multiselect("Baseline Energy Filter (kWh charged during AY2526 BEFORE experimental assignment; 0 - None, 1 - Low, 4 - High):", options=unique_energies, default=unique_energies)
    else:
        selected_energies = None

    if freq_col:
        unique_freqs = sorted(df_chars[freq_col].dropna().astype(str).unique().tolist())
        selected_freqs = st.multiselect("Baseline Frequency Filter (Days with sessions during AY2526 BEFORE experimental assignment; 0 - None, 1 - Low, 4 - High):", options=unique_freqs, default=unique_freqs)
    else:
        selected_freqs = None

    if loc_col:
        unique_locs = sorted(df_chars[loc_col].dropna().astype(str).unique().tolist())
        selected_locs = st.multiselect("Charging Location Group:", options=unique_locs, default=unique_locs)
    else:
        selected_locs = None

    if bring_col:
        unique_brings = sorted(df_chars[bring_col].dropna().astype(str).unique().tolist())
        selected_brings = st.multiselect("kWh Could Bring Filter (1 - Low; 4 - High):", options=unique_brings, default=unique_brings)
    else:
        selected_brings = None

    # --- Sub-section 3: Disaggregation Fields ---
    st.subheader('3. Disaggregation Fields 📊')
    """
    Select variables to define cohorts for visualization. 
    Deselecting all generates aggregate curves.
    """
    disagg_options = {}
    if treatment_col: disagg_options["Treatment"] = treatment_col
    if recency_col:    disagg_options["Recency Status"] = recency_col
    if energy_col:     disagg_options["Baseline Energy"] = energy_col
    if bring_col:      disagg_options["kWh Could Bring"] = bring_col
    if loc_col:        disagg_options["Charging Location"] = loc_col

    default_selections = []
    if "Treatment" in disagg_options: default_selections.append("Treatment")

    selected_disagg_labels = st.multiselect(
        "Disaggregate cohorts by:",
        options=list(disagg_options.keys()),
        default=default_selections
    )
    chosen_disagg_cols = [disagg_options[label] for label in selected_disagg_labels]


    # ==============================================================================
    # DATA PROCESSING PIPELINE (APPROACH 1: FILTER IDS FIRST)
    # ==============================================================================
    
    # 1. Filter the SMALL characteristics dataset first based on user selection inputs
    df_chars_filtered = df_chars.copy()
        
    if selected_treatments is not None:
        active_treatment_filters = [t for t in selected_treatments if t != 'Offer']
        if 'Offer' in selected_treatments:
            active_treatment_filters.extend(offer_components)
        df_chars_filtered = df_chars_filtered[df_chars_filtered[treatment_col].astype(str).isin(active_treatment_filters)]

    if selected_recencies is not None:
        df_chars_filtered = df_chars_filtered[df_chars_filtered[recency_col].astype(str).isin(selected_recencies)]
    if selected_energies is not None:
        df_chars_filtered = df_chars_filtered[df_chars_filtered[energy_col].astype(str).isin(selected_energies)]
    if selected_freqs is not None:
        df_chars_filtered = df_chars_filtered[df_chars_filtered[freq_col].astype(str).isin(selected_freqs)]
    if selected_locs is not None:
        df_chars_filtered = df_chars_filtered[df_chars_filtered[loc_col].astype(str).isin(selected_locs)]
    if selected_brings is not None:
        df_chars_filtered = df_chars_filtered[df_chars_filtered[bring_col].astype(str).isin(selected_brings)]

    # Extract the isolated set of valid driver tracking IDs
    valid_ids = df_chars_filtered[driver_col_id].unique()

    # 2. Slice down the LARGE outcomes dataset by timescale AND the matching valid driver IDs
    df_filtered = df_outcomes[
        (df_outcomes['week'] >= selected_week_range[0]) & 
        (df_outcomes['week'] <= selected_week_range[1]) &
        (df_outcomes[driver_col_id].isin(valid_ids))
    ].copy()
    
    # Free up heavy raw outcomes lookup variable from loop memory immediately
    del df_outcomes

    # 3. Micro-Merge: Bring over ONLY the specific columns required for Disaggregation Groups / Offer Expansion
    cols_to_merge = list(set([driver_col_id] + chosen_disagg_cols + ([treatment_col] if treatment_col else [])))
    df_filtered = pd.merge(df_filtered, df_chars_filtered[cols_to_merge], on=driver_col_id, how='inner')
    
    # Clean up characteristics snapshot slice
    del df_chars_filtered

    # 4. AGGREGATE "OFFER" GROUP CREATION (Post-Filtering on the tiny merged slice)
    if treatment_col and selected_treatments and 'Offer' in selected_treatments:
        df_offer_duplicates = df_filtered[df_filtered[treatment_col].astype(str).isin(offer_components)].copy()
        if not df_offer_duplicates.empty:
            df_offer_duplicates[treatment_col] = 'Offer'
            df_filtered = pd.concat([df_filtered, df_offer_duplicates], ignore_index=True)
        del df_offer_duplicates

    # 5. Generate Core Campus Metrics Baseline
    df_aggregate = df_filtered.drop_duplicates(subset=[driver_col_id, 'week'])

    session_counts = (
        df_aggregate.groupby('week')[sessions_col]
        .sum()
        .reset_index(name='session_count')
        .sort_values('week')
    )
    
    del df_aggregate

    # Deduplicate "Offer" duplication rows if Treatment mapping line display isn't active
    if "Treatment" not in selected_disagg_labels:
        df_filtered = df_filtered.drop_duplicates(subset=[driver_col_id, 'week'])

    df_filtered = df_filtered.copy()

    if df_filtered.empty:
        df_filtered['group'] = ''
    elif chosen_disagg_cols and len(chosen_disagg_cols) > 0:
        df_filtered['group'] = df_filtered[chosen_disagg_cols[0]].astype(str)
        for col in chosen_disagg_cols[1:]:
            df_filtered['group'] = df_filtered['group'] + ' - ' + df_filtered[col].astype(str)
    else:
        df_filtered['group'] = 'All Included Drivers'

    df_filtered = df_filtered[df_filtered['group'] != '']
    df_filtered = df_filtered[~df_filtered['group'].str.lower().str.contains('excluded')]

    unique_groups_present = sorted(df_filtered['group'].unique().tolist())

    # --- Sub-section 4: Active Subgroups and Legend ---
    st.subheader('4. Active Subgroups and Legend 🏷️')
    
    palette_pool = [
        '#0072B2', '#E69F00', '#009E73', '#CC79A7', '#F0E442', 
        '#D55E00', '#56B4E9', '#999999', '#491D88', '#A6C48A'
    ]
    # Pool of symbols chosen to dynamically correspond to the hex tones in palette_pool
    emoji_pool = [
        '🔵', '🟠', '🟢', '🟣', '🟡', 
        '🔴', '🔷', '⚫', '🟪', '💚'
    ]
    
    group_color_map = {}
    group_dash_map = {}
    subgroup_display_labels = {}

    for idx, grp in enumerate(unique_groups_present):
        color_index = idx % len(palette_pool)
        group_color_map[grp] = palette_pool[color_index]
        group_dash_map[grp] = []  # Explicitly reset line dash metrics for solid lines
        
        # Pull the matching emoji index to pair perfectly with the visual representation colors
        icon = emoji_pool[color_index]

        line_style = "─"
        subgroup_display_labels[grp] = f"{icon} {line_style} {grp}"

    selected_subgroups = []
    if unique_groups_present:
        col_left, col_right = st.columns(2)
        for i, grp in enumerate(unique_groups_present):
            target_col = col_left if i % 2 == 0 else col_right
            if target_col.checkbox(subgroup_display_labels[grp], value=True):
                selected_subgroups.append(grp)
    else:
        st.info("No active cohorts found with current configuration choices.")

    if 'active' in df_filtered.columns:
        df_filtered['active'] = pd.to_numeric(df_filtered['active'], errors='coerce')
        df_active_weekly = df_filtered[df_filtered['active'] == 1]
    else:
        df_active_weekly = df_filtered

    weekly_active_scale = (
        df_active_weekly.groupby(['week', 'group'])[driver_col_id]
        .nunique()
        .reset_index(name='active_driver_count')
    )
    
    del df_active_weekly

    # ==============================================================================
    # RESULTS SECTION
    # ==============================================================================
    st.markdown("---")
    st.header('Results & Graphical Insights 📈')

    # Construct Event Markers Layer
    if show_events and not event_markers.empty:
        event_markers_filtered = event_markers[
            (event_markers['week'] >= selected_week_range[0]) & 
            (event_markers['week'] <= selected_week_range[1])
        ].copy()
        
        if not event_markers_filtered.empty:
            event_rule = alt.Chart(event_markers_filtered).mark_rule(
                color='#555555', strokeWidth=1, strokeDash=[2, 2], opacity=0.9
            ).encode(
                x=alt.X('week:Q', scale=alt.Scale(domain=list(selected_week_range), clamp=True)),
                tooltip=[alt.Tooltip('week:Q', title='Event Week'), alt.Tooltip('event_detail:N', title='Detail')]
            )
            
            event_text = alt.Chart(event_markers_filtered).mark_text(
                align='left', baseline='middle', dx=5, dy=5, angle=270, color='#666666', fontSize=10
            ).encode(
                x=alt.X('week:Q', scale=alt.Scale(domain=list(selected_week_range), clamp=True)),
                y=alt.value(270),  
                text='event_detail:N'
            )
        else:
            event_rule = None
            event_text = None
    else:
        event_rule = None
        event_text = None

    # Construct Holiday Bars Layer (Properly Indented to remain within 'week' filter scope)
    if not holiday_markers.empty:
        holiday_markers_filtered = holiday_markers[
            (holiday_markers['week'] >= selected_week_range[0]) & 
            (holiday_markers['week'] <= selected_week_range[1])
        ].copy()
        
        if not holiday_markers_filtered.empty:
            holiday_thin = holiday_markers_filtered[holiday_markers_filtered['ucsd_holiday'] <= 2]
            holiday_thick = holiday_markers_filtered[holiday_markers_filtered['ucsd_holiday'] > 2]
            
            holiday_layers = []
            if not holiday_thin.empty:
                holiday_layers.append(
                    alt.Chart(holiday_thin).mark_rule(color='#D3D3D3', strokeWidth=3, opacity=0.4).encode(
                        x=alt.X('week:Q', scale=alt.Scale(domain=list(selected_week_range), clamp=True)),
                        tooltip=[alt.Tooltip('week:Q', title='Holiday Week'), alt.Tooltip('ucsd_holiday:Q', title='Holiday Level')]
                    )
                )
            if not holiday_thick.empty:
                holiday_layers.append(
                    alt.Chart(holiday_thick).mark_rule(color='#D3D3D3', strokeWidth=8, opacity=0.4).encode(
                        x=alt.X('week:Q', scale=alt.Scale(domain=list(selected_week_range), clamp=True)),
                        tooltip=[alt.Tooltip('week:Q', title='Holiday Week'), alt.Tooltip('ucsd_holiday:Q', title='Holiday Level')]
                    )
                )
            holiday_rule = alt.layer(*holiday_layers) if holiday_layers else None
        else:
            holiday_rule = None
    else:
        holiday_rule = None

    st.header('Weekly Outcomes Across Selected Timescale')

    # --- PLOT 1: Total Campus Sessions ---
    st.subheader('Total Sessions per Week')
    if not session_counts.empty:
        session_chart = (
            alt.Chart(session_counts)
            .mark_line(point=True, clip=True)
            .encode(
                x=alt.X('week:Q', title='Week', scale=alt.Scale(domain=list(selected_week_range), clamp=True)),
                y=alt.Y('session_count:Q', title='Campus Weekly Sessions'),
                tooltip=[alt.Tooltip('week:Q', title='Week'), alt.Tooltip('session_count:Q', title='Total Sessions')]
            )
        )
        
        # Layering Pipeline
        session_layers = []
        if holiday_rule is not None:
            session_layers.append(holiday_rule)
        if event_rule is not None:
            session_layers.append(event_rule)
        session_layers.append(session_chart)
        if event_text is not None:
            session_layers.append(event_text)
            
        session_chart = alt.layer(*session_layers).resolve_scale(y='shared')
        st.altair_chart(session_chart, width='stretch')
    else:
        st.warning("No data rows available to draw total aggregate sessions.")

    # --- PLOT 2: Daily Sessions by Subgroup ---
    st.subheader('Daily Sessions By Group')
    if selected_subgroups:
        grouped_counts = (
            df_filtered[df_filtered['group'].isin(selected_subgroups)]
            .groupby(['week', 'group'])[sessions_col]
            .sum()
            .reset_index(name='session_count')
            .sort_values(['group', 'week'])
        )
        
        show_daily_sessions = st.checkbox("Show Total Daily Sessions By Group", value=False)
        if show_daily_sessions:
            filtered_group_counts_daily = grouped_counts.copy()
            filtered_group_counts_daily['session_count'] = filtered_group_counts_daily['session_count'] / 7.0

            grouped_chart = (
                alt.Chart(filtered_group_counts_daily)
                .mark_line(point=True, clip=True)
                .encode(
                    x=alt.X('week:Q', title='Week', scale=alt.Scale(domain=list(selected_week_range), clamp=True)),
                    y=alt.Y('session_count:Q', title='Campus Sessions Per Day'),
                    color=alt.Color('group:N', title='Group', scale=alt.Scale(domain=list(group_color_map.keys()), range=list(group_color_map.values()))),
                    strokeDash=alt.StrokeDash('group:N', scale=alt.Scale(domain=list(group_dash_map.keys()), range=list(group_dash_map.values()))),
                    tooltip=[alt.Tooltip('week:Q', title='Week'), alt.Tooltip('group:N', title='Group'), alt.Tooltip('session_count:Q', title='Sessions/Day', format='.1f')]
                )
            )
            
            # Layering Pipeline
            grouped_layers = []
            if holiday_rule is not None:
                grouped_layers.append(holiday_rule)
            if event_rule is not None:
                grouped_layers.append(event_rule)
            grouped_layers.append(grouped_chart)
            if event_text is not None:
                grouped_layers.append(event_text)
                
            grouped_chart = alt.layer(*grouped_layers).resolve_scale(y='shared')
            st.altair_chart(grouped_chart, width='stretch')

        # --- PLOT 3: Sessions Per Capita ---
        st.subheader('Sessions per Capita per Week by Group')
        scaled_counts = grouped_counts.copy()
        
        scaled_counts = pd.merge(scaled_counts, weekly_active_scale, on=['week', 'group'], how='left')
        scaled_counts['active_driver_count'] = scaled_counts['active_driver_count'].fillna(1).replace(0, 1)
        scaled_counts['session_count'] = scaled_counts['session_count'] / scaled_counts['active_driver_count']
        
        scaled_chart = (
            alt.Chart(scaled_counts)
            .mark_line(point=True, clip=True)
            .encode(
                x=alt.X('week:Q', title='Week', scale=alt.Scale(domain=list(selected_week_range), clamp=True)),
                y=alt.Y('session_count:Q', title='Campus Sessions Per Capita Per Week'),
                color=alt.Color('group:N', title='Group', scale=alt.Scale(domain=list(group_color_map.keys()), range=list(group_color_map.values())), legend=alt.Legend(orient='bottom')),
                strokeDash=alt.StrokeDash('group:N', scale=alt.Scale(domain=list(group_dash_map.keys()), range=list(group_dash_map.values())), legend=alt.Legend(orient='bottom')),
                tooltip=[alt.Tooltip('week:Q', title='Week'), alt.Tooltip('group:N', title='Group'), alt.Tooltip('session_count:Q', title='Sessions/Capita', format='.2f')]
            )
        )
        
        # Layering Pipeline
        scaled_layers = []
        if holiday_rule is not None:
            scaled_layers.append(holiday_rule)
        if event_rule is not None:
            scaled_layers.append(event_rule)
        scaled_layers.append(scaled_chart)
        if event_text is not None:
            scaled_layers.append(event_text)
            
        scaled_chart = alt.layer(*scaled_layers).resolve_scale(y='shared')
        st.altair_chart(scaled_chart, width='stretch')
    else:
        st.info("Check one or more subgroups above to view cohort line comparison charts.")

    # --- PLOTS 4 & 5: Energy Delivery (kWh) ---
    kwh_col = 'kwh_sum' if 'kwh_sum' in df_filtered.columns else ('energy' if 'energy' in df_filtered.columns else None)
    
    if kwh_col and selected_subgroups:
        df_filtered[kwh_col] = pd.to_numeric(df_filtered[kwh_col], errors='coerce')
        grouped_kwh = (
            df_filtered[df_filtered['group'].isin(selected_subgroups)]
            .dropna(subset=[kwh_col])
            .groupby(['week', 'group'])
            .agg(kwh_sum=(kwh_col, 'sum'))
            .reset_index()
            .sort_values(['group', 'week'])
        )
        
        st.subheader('Weekly kWh by Group')
        show_weekly_kwh = st.checkbox("Show Total Weekly kWh by Group", value=False)
        if show_weekly_kwh:
            kwh_chart = (
                alt.Chart(grouped_kwh)
                .mark_line(point=True, clip=True)
                .encode(
                    x=alt.X('week:Q', title='Week', scale=alt.Scale(domain=list(selected_week_range), clamp=True)),
                    y=alt.Y('kwh_sum:Q', title='Weekly kWh'),
                    color=alt.Color('group:N', title='Group', scale=alt.Scale(domain=list(group_color_map.keys()), range=list(group_color_map.values()))),
                    strokeDash=alt.StrokeDash('group:N', scale=alt.Scale(domain=list(group_dash_map.keys()), range=list(group_dash_map.values()))),
                    tooltip=[alt.Tooltip('week:Q', title='Week'), alt.Tooltip('group:N', title='Group'), alt.Tooltip('kwh_sum:Q', title='Total kWh', format='.0f')]
                )
            )
            
            # Layering Pipeline
            kwh_layers = []
            if holiday_rule is not None:
                kwh_layers.append(holiday_rule)
            if event_rule is not None:
                kwh_layers.append(event_rule)
            kwh_layers.append(kwh_chart)
            if event_text is not None:
                kwh_layers.append(event_text)
                
            kwh_chart = alt.layer(*kwh_layers).resolve_scale(y='shared')
            st.altair_chart(kwh_chart, width='stretch')

        # --- PLOT 5: kWh Per Capita ---
        st.subheader('kWh per Capita per Week by Group')
        scaled_kwh = grouped_kwh.copy()
        
        scaled_kwh = pd.merge(scaled_kwh, weekly_active_scale, on=['week', 'group'], how='left')
        scaled_kwh['active_driver_count'] = scaled_kwh['active_driver_count'].fillna(1).replace(0, 1)
        scaled_kwh['kwh_sum'] = scaled_kwh['kwh_sum'] / scaled_kwh['active_driver_count']
        
        scaled_kwh_chart = (
            alt.Chart(scaled_kwh)
            .mark_line(point=True, clip=True)
            .encode(
                x=alt.X('week:Q', title='Week', scale=alt.Scale(domain=list(selected_week_range), clamp=True)),
                y=alt.Y('kwh_sum:Q', title='Weekly kWh per Capita'),
                color=alt.Color('group:N', title='Group', scale=alt.Scale(domain=list(group_color_map.keys()), range=list(group_color_map.values())), legend=alt.Legend(orient='bottom')),
                strokeDash=alt.StrokeDash('group:N', scale=alt.Scale(domain=list(group_dash_map.keys()), range=list(group_dash_map.values())), legend=alt.Legend(orient='bottom')),
                tooltip=[alt.Tooltip('week:Q', title='Week'), alt.Tooltip('group:N', title='Group'), alt.Tooltip('kwh_sum:Q', title='kWh/Capita', format='.1f')]
            )
        )
        
        # Layering Pipeline
        scaled_kwh_layers = []
        if holiday_rule is not None:
            scaled_kwh_layers.append(holiday_rule)
        if event_rule is not None:
            scaled_kwh_layers.append(event_rule)
        scaled_kwh_layers.append(scaled_kwh_chart)
        if event_text is not None:
            scaled_kwh_layers.append(event_text)
            
        scaled_kwh_chart = alt.layer(*scaled_kwh_layers).resolve_scale(y='shared')
        st.altair_chart(scaled_kwh_chart, width='stretch')
    elif not kwh_col:
        st.warning("The dataset does not contain energy consumption metrics ('kwh_sum' or 'energy').")

    st.header('Aggregate Outcomes Since Discounts Launch')

    # --- SUMMARY STATISTICS (POST WEEK 170) ---
    summary_since_week170 = df_filtered[(df_filtered['week'] >= 170) & (df_filtered['group'].isin(selected_subgroups))].copy()
    
    if selected_subgroups and not summary_since_week170.empty:
        if 'active' in summary_since_week170.columns:
            summary_since_week170['active'] = pd.to_numeric(summary_since_week170['active'], errors='coerce')
            summary_active_drivers = summary_since_week170[summary_since_week170['active'] == 1]
        else:
            summary_active_drivers = summary_since_week170
            
        summary_scale_map = {}
        for grp in selected_subgroups:
            unique_active_count = summary_active_drivers[summary_active_drivers['group'] == grp][driver_col_id].nunique()
            summary_scale_map[grp] = unique_active_count if unique_active_count > 0 else 1

        # Summary Chart 1: Total kWh Per Capita
        if kwh_col:
            summary_since_week170[kwh_col] = pd.to_numeric(summary_since_week170[kwh_col], errors='coerce')
            kwh_totals = (
                summary_since_week170.groupby('group')
                .agg(total_kwh=(kwh_col, 'sum'))
                .reset_index()
                .sort_values('group')
            )
            kwh_totals['total_kwh'] = kwh_totals['total_kwh'] / kwh_totals['group'].map(summary_scale_map).fillna(1)
            
            st.subheader('Total kWh per Capita by Subgroup')
            kwh_totals_chart = (
                alt.Chart(kwh_totals)
                .mark_bar()
                .encode(
                    x=alt.X('group:N', title='Subgroup', sort=list(group_color_map.keys())),
                    y=alt.Y('total_kwh:Q', title='Total kWh'),
                    color=alt.Color('group:N', scale=alt.Scale(domain=list(group_color_map.keys()), range=list(group_color_map.values())), legend=None),
                    tooltip=[alt.Tooltip('group:N', title='Subgroup'), alt.Tooltip('total_kwh:Q', title='Total kWh', format=',.0f')]
                )
            )
            st.altair_chart(kwh_totals_chart, width='stretch')

        # Summary Chart 2: Total Session Duration Per Capita
        sess_dur_col = 'sessionduration_sum' if 'sessionduration_sum' in summary_since_week170.columns else ('session_duration' if 'session_duration' in summary_since_week170.columns else None)
        if sess_dur_col:
            summary_since_week170[sess_dur_col] = pd.to_numeric(summary_since_week170[sess_dur_col], errors='coerce')
            session_duration_totals = (
                summary_since_week170.groupby('group')
                .agg(total_session_duration=(sess_dur_col, 'sum'))
                .reset_index()
                .sort_values('group')
            )
            st.subheader('Total Session Duration per Capita by Subgroup')
            session_duration_totals['total_session_duration'] = session_duration_totals['total_session_duration'] / session_duration_totals['group'].map(summary_scale_map).fillna(1)
            
            session_duration_chart = (
                alt.Chart(session_duration_totals)
                .mark_bar()
                .encode(
                    x=alt.X('group:N', title='Subgroup', sort=list(group_color_map.keys())),
                    y=alt.Y('total_session_duration:Q', title='Total Session Duration'),
                    color=alt.Color('group:N', scale=alt.Scale(domain=list(group_color_map.keys()), range=list(group_color_map.values())), legend=None),
                    tooltip=[alt.Tooltip('group:N', title='Subgroup'), alt.Tooltip('total_session_duration:Q', title='Total Session Duration', format=',.0f')]
                )
            )
            st.altair_chart(session_duration_chart, width='stretch')

        # Summary Chart 3: Total Charging Duration Per Capita
        chg_dur_col = 'chargingduration_sum' if 'chargingduration_sum' in summary_since_week170.columns else ('charging_duration' if 'charging_duration' in summary_since_week170.columns else None)
        if chg_dur_col:
            summary_since_week170[chg_dur_col] = pd.to_numeric(summary_since_week170[chg_dur_col], errors='coerce')
            charging_duration_totals = (
                summary_since_week170.groupby('group')
                .agg(total_charging_duration=(chg_dur_col, 'sum'))
                .reset_index()
                .sort_values('group')
            )
            st.subheader('Total Charging Duration per Capita by Subgroup')
            charging_duration_totals['total_charging_duration'] = charging_duration_totals['total_charging_duration'] / charging_duration_totals['group'].map(summary_scale_map).fillna(1)
            
            charging_duration_chart = (
                alt.Chart(charging_duration_totals)
                .mark_bar()
                .encode(
                    x=alt.X('group:N', title='Subgroup', sort=list(group_color_map.keys())),
                    y=alt.Y('total_charging_duration:Q', title='Total Charging Duration'),
                    color=alt.Color('group:N', scale=alt.Scale(domain=list(group_color_map.keys()), range=list(group_color_map.values())), legend=None),
                    tooltip=[alt.Tooltip('group:N', title='Subgroup'), alt.Tooltip('total_charging_duration:Q', title='Total Charging Duration', format=',.0f')]
                )
            )
            st.altair_chart(charging_duration_chart, width='stretch')

        # Summary Chart 4: Total Charging Days Per Capita
        chg_days_col = 'chargingdays_sum' if 'chargingdays_sum' in summary_since_week170.columns else ('charging_days' if 'charging_days' in summary_since_week170.columns else ('daysofcharging_sum' if 'daysofcharging_sum' in summary_since_week170.columns else None))
        if chg_days_col:
            summary_since_week170[chg_days_col] = pd.to_numeric(summary_since_week170[chg_days_col], errors='coerce')
            charging_days_totals = (
                summary_since_week170.groupby('group')
                .agg(total_charging_days=(chg_days_col, 'sum'))
                .reset_index()
                .sort_values('group')
            )
            st.subheader('Total Charging Days per Capita by Subgroup')
            charging_days_totals['total_charging_days'] = charging_days_totals['total_charging_days'] / charging_days_totals['group'].map(summary_scale_map).fillna(1)
            
            charging_days_chart = (
                alt.Chart(charging_days_totals)
                .mark_bar()
                .encode(
                    x=alt.X('group:N', title='Subgroup', sort=list(group_color_map.keys())),
                    y=alt.Y('total_charging_days:Q', title='Total Charging Days'),
                    color=alt.Color('group:N', scale=alt.Scale(domain=list(group_color_map.keys()), range=list(group_color_map.values())), legend=None),
                    tooltip=[alt.Tooltip('group:N', title='Subgroup'), alt.Tooltip('total_charging_days:Q', title='Total Charging Days', format='.1f')]
                )
            )
            st.altair_chart(charging_days_chart, width='stretch')
    elif selected_subgroups:
        st.warning('No subgroup sessions found on or after week 170 for the selected criteria.')
else:
    st.error("SP26 Research Data is missing the 'week' field required for analysis.")

# ==============================================================================
# POST-RUN CLEANUP SECTION
# ==============================================================================
gc.collect()