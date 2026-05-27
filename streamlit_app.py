import streamlit as st
import json
import pandas as pd
import altair as alt
from pathlib import Path

# ==============================================================================
# HEADER SECTION
# ==============================================================================
st.title("D2I Spring 2026 Subscription Experiment 🚗🔌⚡")
st.write(
    "Data below reflects all Level 2 PowerFlex and ChargePoint sessions associated with the Offer, Gift, and Control groups in the SP26 experiment."
)
"""
# Has the subscription experiment reshaped EV charging behavior? 
Everything below is preliminary and subject to change, with minimal QA/QC done to date. The underlying datasets can be viewed below (but are hidden by default), followed by selectable options (e.g., timescale to view and groups of drivers to display) and then the descriptive figures themselves.
"""

# Load local dataset from the repository's datasets folder.
research_path = Path('data/SP26_userxweek_charging_light_27may26.parquet')

if research_path.exists():
    df_research = pd.read_parquet(research_path)
    st.success(f"Loaded SP26 Research Data dataset from {research_path}")
else:
    df_research = None
    st.warning(f"SP26 Research Data file not found: {research_path}")

show_research_dataset = st.checkbox('Show SP26 Research Data dataset', value=False)
if show_research_dataset:
    if df_research is not None:
        st.write(f"SP26 Research Data contains {len(df_research)} rows and {len(df_research.columns)} columns.")
        st.write('Showing the first 100 rows:')
        st.dataframe(df_research.head(100))
    else:
        st.error('SP26 Research Data dataset is not available.')

if df_research is not None:
    # Ensure alignment with weekly format
    if 'week' in df_research.columns:
        df_research['week'] = pd.to_numeric(df_research['week'], errors='coerce')
        df_research = df_research.dropna(subset=['week'])
        df_research['week'] = df_research['week'].astype(int)

        # Identify the sessions metric column to sum up (attempted_sessions)
        sessions_col = 'attempted_sessions' if 'attempted_sessions' in df_research.columns else ('sessions' if 'sessions' in df_research.columns else None)

        if not sessions_col:
            st.error("Could not find a valid sessions metric column (e.g., 'attempted_sessions') in the dataset.")
            st.stop()

        # Process event markers directly from the weekly data structure
        if 'event' in df_research.columns:
            df_research['event'] = pd.to_numeric(df_research['event'], errors='coerce')
        else:
            df_research['event'] = pd.NA

        if 'event_detail' in df_research.columns:
            df_research['event_detail'] = df_research['event_detail'].astype(str)
        else:
            df_research['event_detail'] = ''

        event_markers = df_research[
            df_research['event'].notna() & 
            (df_research['event_detail'] != '') & 
            (df_research['event_detail'] != 'nan')
        ].copy()

        if not event_markers.empty:
            event_markers = event_markers.drop_duplicates(subset=['week'])
            event_rule = alt.Chart(event_markers).mark_rule(color='#4a4a4a', strokeWidth=3, opacity=0.85).encode(
                x=alt.X('week:Q', scale=alt.Scale(clamp=True)),
                tooltip=[alt.Tooltip('event_detail:N', title='Event detail')]
            )
        else:
            event_rule = None


        # ==============================================================================
        # SETTINGS SECTION
        # ==============================================================================
        st.markdown("---")
        st.header('Configuration Settings 🛠️')
        
        # --- Sub-section 1: Timescale ---
        st.subheader('1. Timescale 📅')
        min_week = int(df_research['week'].min())
        max_week = int(df_research['week'].max())
        
        selected_week_range = st.slider(
            "Select experiment weeks range to display:",
            min_value=min_week,
            max_value=max_week,
            value=(min_week, max_week)
        )

        # --- Sub-section 2: Inclusion Criteria ---
        st.subheader('2. Inclusion Criteria 🔍')
        st.caption("Determine which driver-weeks pass the filtering rules to be used in final analytics.")
        
        # Mapping base tracking metrics explicitly
        drivetrain_col = 'autotypenew' if 'autotypenew' in df_research.columns else None
        treatment_col = 'treatment' if 'treatment' in df_research.columns else None
        recency_col = 'lastperiodcharged' if 'lastperiodcharged' in df_research.columns else None
        energy_col = 'baselinekwhcharged' if 'baselinekwhcharged' in df_research.columns else None
        freq_col = 'baselinedaysofcharging' if 'baselinedaysofcharging' in df_research.columns else None
        loc_col = 'charginglocgroup' if 'charginglocgroup' in df_research.columns else None
        bring_col = 'kwhcouldbringtocampus' if 'kwhcouldbringtocampus' in df_research.columns else None

        # Displaying criteria sequentially down a single clean vertical column
        if drivetrain_col:
            unique_drivetrains = sorted(df_research[drivetrain_col].dropna().unique().tolist())
            selected_drivetrains = st.multiselect("Drivetrain Filter (autotypenew):", options=unique_drivetrains, default=unique_drivetrains)
        else:
            selected_drivetrains = None

        if treatment_col:
            unique_treatments = sorted(df_research[treatment_col].dropna().unique().tolist())
            selected_treatments = st.multiselect("Treatment Group Filter (treatment):", options=unique_treatments, default=unique_treatments)
        else:
            selected_treatments = None

        if recency_col:
            unique_recencies = sorted(df_research[recency_col].dropna().unique().tolist())
            selected_recencies = st.multiselect("Charge Recency Filter:", options=unique_recencies, default=unique_recencies)
        else:
            selected_recencies = None

        if energy_col:
            unique_energies = sorted(df_research[energy_col].dropna().astype(str).unique().tolist())
            selected_energies = st.multiselect("Baseline Energy Filter (baselinekwhcharged):", options=unique_energies, default=unique_energies)
        else:
            selected_energies = None

        if freq_col:
            unique_freqs = sorted(df_research[freq_col].dropna().astype(str).unique().tolist())
            selected_freqs = st.multiselect("Baseline Frequency Filter (baselinedaysofcharging):", options=unique_freqs, default=unique_freqs)
        else:
            selected_freqs = None

        if loc_col:
            unique_locs = sorted(df_research[loc_col].dropna().unique().tolist())
            selected_locs = st.multiselect("Charging Location Group:", options=unique_locs, default=unique_locs)
        else:
            selected_locs = None

        if bring_col:
            unique_brings = sorted(df_research[bring_col].dropna().astype(str).unique().tolist())
            selected_brings = st.multiselect("kWh Could Bring Filter (kwhcouldbringtocampus):", options=unique_brings, default=unique_brings)
        else:
            selected_brings = None


        # --- Sub-section 3: Disaggregation Fields ---
        st.subheader('3. Disaggregation Fields 📊')
        st.caption("Select variables to cross-reference cohorts. Selecting none generates aggregate curves.")
        
        # Build option mapping matrix (Maintains compatibility with string formats)
        disagg_options = {}
        if treatment_col: disagg_options["Treatment"] = treatment_col
        if drivetrain_col: disagg_options["Vehicle Drivetrain"] = drivetrain_col
        if recency_col:    disagg_options["Recency Status"] = recency_col
        if energy_col:     disagg_options["Baseline Energy"] = energy_col
        if bring_col:      disagg_options["kWh Could Bring"] = bring_col
        if loc_col:        disagg_options["Charging Location"] = loc_col

        default_selections = []
        if "Treatment" in disagg_options: default_selections.append("Treatment")
        if "Vehicle Drivetrain" in disagg_options: default_selections.append("Vehicle Drivetrain")

        selected_disagg_labels = st.multiselect(
            "Disaggregate cohorts by:",
            options=list(disagg_options.keys()),
            default=default_selections
        )
        chosen_disagg_cols = [disagg_options[label] for label in selected_disagg_labels]


        # ==============================================================================
        # DATA PROCESSING PIPELINE
        # ==============================================================================
        
        # 1. Apply Timescale Filter Boundary Range
        df_filtered = df_research[
            (df_research['week'] >= selected_week_range[0]) & 
            (df_research['week'] <= selected_week_range[1])
        ].copy()

        # 2. Apply Inclusion Criteria Categorical Filters (Updated with categorical string support)
        if selected_drivetrains is not None:
            df_filtered = df_filtered[df_filtered[drivetrain_col].isin(selected_drivetrains)]
        if selected_treatments is not None:
            df_filtered = df_filtered[df_filtered[treatment_col].isin(selected_treatments)]
        if selected_recencies is not None:
            df_filtered = df_filtered[df_filtered[recency_col].isin(selected_recencies)]
        if selected_energies is not None:
            df_filtered = df_filtered[df_filtered[energy_col].astype(str).isin(selected_energies)]
        if selected_freqs is not None:
            df_filtered = df_filtered[df_filtered[freq_col].astype(str).isin(selected_freqs)]
        if selected_locs is not None:
            df_filtered = df_filtered[df_filtered[loc_col].isin(selected_locs)]
        if selected_brings is not None:
            df_filtered = df_filtered[df_filtered[bring_col].astype(str).isin(selected_brings)]

        # 4. Generate Core Campus Metrics Baseline
        session_counts = (
            df_filtered.groupby('week')[sessions_col]
            .sum()
            .reset_index(name='session_count')
            .sort_values('week')
        )

        # 5. Clean Dynamic Group Evaluation Logic
        # FIX: Explicitly forces row-by-row string flattening via lambda to fix DataFrame assignment crashes
        if chosen_disagg_cols:
            df_filtered['group'] = df_filtered[chosen_disagg_cols].astype(str).apply(lambda row: ' - '.join(row), axis=1)
        else:
            df_filtered['group'] = 'All Included Drivers'

        # Filter out unassigned or residual records
        df_filtered = df_filtered[df_filtered['group'] != '']
        df_filtered = df_filtered[~df_filtered['group'].str.lower().str.contains('excluded')]

        # Discover unique groups containing at least one real matching record
        unique_groups_present = sorted(df_filtered['group'].unique().tolist())


        # --- Sub-section 4: Active Subgroups and Legend ---
        st.subheader('4. Active Subgroups and Legend 🏷️')
        
        # Colorblind-friendly custom high-contrast categorical palette (e.g., Okabe-Ito / Wong inspired)
        palette_pool = [
            '#0072B2',  # Clear Blue
            '#E69F00',  # Orange
            '#009E73',  # Bluish Green
            '#CC79A7',  # Reddish Purple
            '#F0E442',  # Yellow
            '#D55E00',  # Vermilion
            '#56B4E9',  # Sky Blue
            '#999999',  # Neutral Gray
            '#491D88',  # Dark Violet
            '#A6C48A'   # Soft Sage Green
        ]
        
        group_color_map = {}
        group_dash_map = {}
        subgroup_display_labels = {}

        for idx, grp in enumerate(unique_groups_present):
            color_index = idx % len(palette_pool)
            group_color_map[grp] = palette_pool[color_index]
            
            group_dash_map[grp] = [5, 5] if 'phev' in grp.lower() else []
            
            icon = "⚪"
            if "control" in grp.lower(): icon = "🔴"
            elif "gift" in grp.lower(): icon = "🔵"
            elif "offer" in grp.lower(): icon = "🟢"
            elif "enrolled" in grp.lower(): icon = "🟡"

            line_style = "╌" if 'phev' in grp.lower() else "─"
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

        # 6. Sample Footprint Count Capacity Dynamic Allocator Engine
        scale_map = {}
        driver_col_id = 'driver' if 'driver' in df_filtered.columns else ('userid' if 'userid' in df_filtered.columns else df_filtered.columns[0])
        for grp in unique_groups_present:
            driver_count = df_filtered[df_filtered['group'] == grp][driver_col_id].nunique()
            scale_map[grp] = driver_count if driver_count > 0 else 1


        # ==============================================================================
        # RESULTS SECTION
        # ==============================================================================
        st.markdown("---")
        st.header('Results & Graphical Insights 📈')

        # --- PLOT 1: Total Campus Sessions ---
        st.subheader('Sessions per Week')
        
        if not session_counts.empty:
            session_chart = (
                alt.Chart(session_counts)
                .mark_line(point=True)
                .encode(
                    x=alt.X('week:Q', title='Experiment Week', scale=alt.Scale(domain=list(selected_week_range), clamp=True)),
                    y=alt.Y('session_count:Q', title='Campus Weekly Sessions')
                )
            )
            if event_rule is not None:
                session_chart = alt.layer(session_chart, event_rule)
            st.altair_chart(session_chart, use_container_width=True)
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
            
            filtered_group_counts_daily = grouped_counts.copy()
            filtered_group_counts_daily['session_count'] = filtered_group_counts_daily['session_count'] / 7.0

            grouped_chart = (
                alt.Chart(filtered_group_counts_daily)
                .mark_line(point=True)
                .encode(
                    x=alt.X('week:Q', title='Experiment Week', scale=alt.Scale(domain=list(selected_week_range), clamp=True)),
                    y=alt.Y('session_count:Q', title='Campus Sessions Per Day'),
                    color=alt.Color('group:N', title='Group', scale=alt.Scale(domain=list(group_color_map.keys()), range=list(group_color_map.values()))),
                    strokeDash=alt.StrokeDash('group:N', scale=alt.Scale(domain=list(group_dash_map.keys()), range=list(group_dash_map.values())))
                )
            )
            if event_rule is not None:
                grouped_chart = alt.layer(grouped_chart, event_rule)
            st.altair_chart(grouped_chart, use_container_width=True)

            # --- PLOT 3: Sessions Per Capita ---
            st.subheader('Sessions per Capita per Week by Group')
            scaled_counts = grouped_counts.copy()
            scaled_counts['session_count'] = scaled_counts.apply(
                lambda row: row['session_count'] / scale_map.get(row['group'], 1),
                axis=1
            )
            scaled_chart = (
                alt.Chart(scaled_counts)
                .mark_line(point=True)
                .encode(
                    x=alt.X('week:Q', title='Experiment Week', scale=alt.Scale(domain=list(selected_week_range), clamp=True)),
                    y=alt.Y('session_count:Q', title='Campus Sessions Per Capita Per Week'),
                    color=alt.Color('group:N', title='Group', scale=alt.Scale(domain=list(group_color_map.keys()), range=list(group_color_map.values()))),
                    strokeDash=alt.StrokeDash('group:N', scale=alt.Scale(domain=list(group_dash_map.keys()), range=list(group_dash_map.values())))
                )
            )
            if event_rule is not None:
                scaled_chart = alt.layer(scaled_chart, event_rule)
            st.altair_chart(scaled_chart, use_container_width=True)
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
            kwh_chart = (
                alt.Chart(grouped_kwh)
                .mark_line(point=True)
                .encode(
                    x=alt.X('week:Q', title='Experiment Week', scale=alt.Scale(domain=list(selected_week_range), clamp=True)),
                    y=alt.Y('kwh_sum:Q', title='Weekly kWh'),
                    color=alt.Color('group:N', title='Group', scale=alt.Scale(domain=list(group_color_map.keys()), range=list(group_color_map.values()))),
                    strokeDash=alt.StrokeDash('group:N', scale=alt.Scale(domain=list(group_dash_map.keys()), range=list(group_dash_map.values())))
                )
            )
            if event_rule is not None:
                kwh_chart = alt.layer(kwh_chart, event_rule)
            st.altair_chart(kwh_chart, use_container_width=True)

            st.subheader('kWh per Capita per Week by Group')
            scaled_kwh = grouped_kwh.copy()
            scaled_kwh['kwh_sum'] = scaled_kwh.apply(
                lambda row: row['kwh_sum'] / scale_map.get(row['group'], 1),
                axis=1
            )
            scaled_kwh_chart = (
                alt.Chart(scaled_kwh)
                .mark_line(point=True)
                .encode(
                    x=alt.X('week:Q', title='Experiment Week', scale=alt.Scale(domain=list(selected_week_range), clamp=True)),
                    y=alt.Y('kwh_sum:Q', title='Weekly kWh per Capita'),
                    color=alt.Color('group:N', title='Group', scale=alt.Scale(domain=list(group_color_map.keys()), range=list(group_color_map.values()))),
                    strokeDash=alt.StrokeDash('group:N', scale=alt.Scale(domain=list(group_dash_map.keys()), range=list(group_dash_map.values())))
                )
            )
            if event_rule is not None:
                scaled_kwh_chart = alt.layer(scaled_kwh_chart, event_rule)
            st.altair_chart(scaled_kwh_chart, use_container_width=True)
        elif not kwh_col:
            st.warning("The dataset does not contain energy consumption metrics ('kwh_sum' or 'energy').")

        # --- SUMMARY STATISTICS (POST WEEK 167) ---
        summary_since_week167 = df_filtered[(df_filtered['week'] >= 167) & (df_filtered['group'].isin(selected_subgroups))].copy()
        
        if selected_subgroups and not summary_since_week167.empty:
            if kwh_col:
                summary_since_week167[kwh_col] = pd.to_numeric(summary_since_week167[kwh_col], errors='coerce')
                kwh_totals = (
                    summary_since_week167.groupby('group')
                    .agg(total_kwh=(kwh_col, 'sum'))
                    .reset_index()
                    .sort_values('group')
                )
                kwh_totals['total_kwh'] = kwh_totals.apply(
                    lambda row: row['total_kwh'] / scale_map.get(row['group'], 1),
                    axis=1
                )
                st.subheader('Total kWh per Capita by Subgroup (Since Week 167)')
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
                st.altair_chart(kwh_totals_chart, use_container_width=True)

            # Duration columns handling fallbacks
            sess_dur_col = 'sessionduration_sum' if 'sessionduration_sum' in summary_since_week167.columns else ('session_duration' if 'session_duration' in summary_since_week167.columns else None)
            if sess_dur_col:
                summary_since_week167[sess_dur_col] = pd.to_numeric(summary_since_week167[sess_dur_col], errors='coerce')
                session_duration_totals = (
                    summary_since_week167.groupby('group')
                    .agg(total_session_duration=(sess_dur_col, 'sum'))
                    .reset_index()
                    .sort_values('group')
                )
                st.subheader('Total Session Duration per Capita by Subgroup (Since Week 167)')
                session_duration_totals['total_session_duration'] = session_duration_totals.apply(
                    lambda row: row['total_session_duration'] / scale_map.get(row['group'], 1),
                    axis=1
                )
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
                st.altair_chart(session_duration_chart, use_container_width=True)

            chg_dur_col = 'chargingduration_sum' if 'chargingduration_sum' in summary_since_week167.columns else ('charging_duration' if 'charging_duration' in summary_since_week167.columns else None)
            if chg_dur_col:
                summary_since_week167[chg_dur_col] = pd.to_numeric(summary_since_week167[chg_dur_col], errors='coerce')
                charging_duration_totals = (
                    summary_since_week167.groupby('group')
                    .agg(total_charging_duration=(chg_dur_col, 'sum'))
                    .reset_index()
                    .sort_values('group')
                )
                st.subheader('Total Charging Duration per Capita by Subgroup (Since Week 167)')
                charging_duration_totals['total_charging_duration'] = charging_duration_totals.apply(
                    lambda row: row['total_charging_duration'] / scale_map.get(row['group'], 1),
                    axis=1
                )
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
                st.altair_chart(charging_duration_chart, use_container_width=True)
        elif selected_subgroups:
            st.warning('No subgroup sessions found on or after week 167 for the selected criteria.')
else:
    st.error("SP26 Research Data is missing the 'week' field required for analysis.")