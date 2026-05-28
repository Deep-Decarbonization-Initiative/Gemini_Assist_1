import streamlit as st
import json
import pandas as pd
import altair as alt
from pathlib import Path

# ==============================================================================
# HEADER SECTION
# ==============================================================================
st.title("D2I Subscription Experiment")
st.title("Spring 2026 🚗🔌⚡")
st.write(
    "Data below reflects all Level 2 PowerFlex and ChargePoint sessions associated with the Offer, Gift, and Control groups in the SP26 experiment." \
    "It does not include any data from non-Triton Charger drivers, nor any data from Triton Chargers who were ineligible for the experiment."
)
"""
# Has the subscription experiment reshaped EV charging behavior? 
Everything below is preliminary and subject to change, with minimal QA/QC done to date. The underlying datasets can be viewed below (but are hidden by default), followed by selectable options (e.g., timescale to view and groups of drivers to display) and then the descriptive figures themselves.
"""

# Load local dataset from the repository's datasets folder.
research_path = Path('data/SP26_userxweek_charging_light_28may26.parquet')

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

        # Event rule visualization configurations (Dotted + 0.9 Opacity)
        if not event_markers.empty:
            event_markers = event_markers.drop_duplicates(subset=['week'])
            
            # 1. Thinner, background vertical dotted line rule
            event_rule = alt.Chart(event_markers).mark_rule(
                color='#808080', 
                strokeWidth=1, 
                strokeDash=[2, 2],
                opacity=0.9
            ).encode(
                x=alt.X('week:Q', scale=alt.Scale(clamp=True))
            )
            
            # 2. Static text label running vertically from bottom to top
            event_text = alt.Chart(event_markers).mark_text(
                align='left',
                baseline='middle',
                dx=5,
                dy=0,
                angle=270,
                color='#666666',
                fontSize=10
            ).encode(
                x=alt.X('week:Q'),
                y=alt.value(270),  # Positioned near the bottom axis, extending upwards
                text='event_detail:N'
            )
        else:
            event_rule = None
            event_text = None


        # ==============================================================================
        # SETTINGS SECTION
        # ==============================================================================
        st.markdown("---")
        st.header('Configuration Settings 🛠️')
        """
       The following sections control what data is visualized and how it is disaggregated in the plots that follow.
       The timescale slider dynamically adjusts the timeframe on the figures. 
       The Inclusion Criteria section can be adjusted to exclude data associated with certain field values (e.g., PHEVs, a particular treatment group, or drivers who hadn't charged since any given academic year (AY)).
       The Disaggregation Fields then determine how to group the remaining data (e.g., by drivetrain, treatment group, and/or given covariates).
        
        """
        # --- Sub-section 1: Timescale ---
        st.subheader('1. Timescale 📅')
        min_week = int(df_research['week'].min())
        max_week = int(df_research['week'].max())
        
        selected_week_range = st.slider(
            "Select range of weeks to display below. These are indexed to January 1st, 2023. " \
            "For reference, the SP26 experimental offers went out during week 167, discounts began week 170, and discounts will end week 183:",
            min_value=min_week,
            max_value=max_week,
            value=(min_week, max_week)
        )

        # Event Visibility Toggle Checkbox (Defaulted to True)
        show_events = st.checkbox("Display event dates.", value=True)
        """
        Dotted vertical lines indicate significant events in the club's history, including key experiment dates.
        """
        # --- Sub-section 2: Inclusion Criteria ---
        st.subheader('2. Inclusion Criteria: Treatment Groups and Covariates 🔍')
        """
        These options determine which driver-weeks pass the filtering rules to be used in final analytics.
        """
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
            selected_drivetrains = st.multiselect("Drivetrain Filter (BEV, PHEV):", options=unique_drivetrains, default=unique_drivetrains)
        else:
            selected_drivetrains = None

        if treatment_col:
            unique_treatments = sorted(df_research[treatment_col].dropna().unique().tolist())
            selected_treatments = st.multiselect("Treatment Group Filter (Note: Left refers to drivers who enrolled but did not pay)):", options=unique_treatments, default=unique_treatments)
        else:
            selected_treatments = None

        if recency_col:
            unique_recencies = sorted(df_research[recency_col].dropna().unique().tolist())
            selected_recencies = st.multiselect("Charge Recency Filter (Academic year of most recent charge BEFORE experimental assignment):", options=unique_recencies, default=unique_recencies)
        else:
            selected_recencies = None

        if energy_col:
            unique_energies = sorted(df_research[energy_col].dropna().astype(str).unique().tolist())
            selected_energies = st.multiselect("Baseline Energy Filter (kWh charged during AY2526 BEFORE experimental assignment; 0 - None, 1 - Low, 4 - High):", options=unique_energies, default=unique_energies)
        else:
            selected_energies = None

        if freq_col:
            unique_freqs = sorted(df_research[freq_col].dropna().astype(str).unique().tolist())
            selected_freqs = st.multiselect("Baseline Frequency Filter (Days with sessions during AY2526 BEFORE experimental assignment; 0 - None, 1 - Low, 4 - High):", options=unique_freqs, default=unique_freqs)
        else:
            selected_freqs = None

        if loc_col:
            unique_locs = sorted(df_research[loc_col].dropna().unique().tolist())
            selected_locs = st.multiselect("Charging Location Group:", options=unique_locs, default=unique_locs)
        else:
            selected_locs = None

        if bring_col:
            unique_brings = sorted(df_research[bring_col].dropna().astype(str).unique().tolist())
            selected_brings = st.multiselect("kWh Could Bring Filter (1 - Low; 4 - High):", options=unique_brings, default=unique_brings)
        else:
            selected_brings = None


        # --- Sub-section 3: Disaggregation Fields ---
        st.subheader('3. Disaggregation Fields 📊')
        """
        Select variables to define cohorts for visualization. 
        Deselecting all generates aggregate curves.
        """
        
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
        if df_filtered.empty:
            df_filtered['group'] = ''
        elif chosen_disagg_cols and len(chosen_disagg_cols) > 0:
            df_filtered['group'] = df_filtered[chosen_disagg_cols[0]].astype(str)
            for col in chosen_disagg_cols[1:]:
                df_filtered['group'] = df_filtered['group'] + ' - ' + df_filtered[col].astype(str)
        else:
            df_filtered['group'] = 'All Included Drivers'

        # Filter out unassigned or residual records
        df_filtered = df_filtered[df_filtered['group'] != '']
        df_filtered = df_filtered[~df_filtered['group'].str.lower().str.contains('excluded')]

        # Discover unique groups containing at least one real matching record
        unique_groups_present = sorted(df_filtered['group'].unique().tolist())


        # --- Sub-section 4: Active Subgroups and Legend ---
        st.subheader('4. Active Subgroups and Legend 🏷️')
        
        # Colorblind-friendly custom high-contrast categorical palette (Wong & Okabe-Ito optimized)
        palette_pool = [
            '#0072B2',  # Deep Clear Blue
            '#E69F00',  # Warm Orange
            '#009E73',  # Bluish Green
            '#CC79A7',  # Reddish Purple
            '#F0E442',  # Distinct Soft Yellow
            '#D55E00',  # Vermilion/Red-Orange
            '#56B4E9',  # Light Sky Blue
            '#999999',  # Medium Gray
            '#491D88',  # Dark Blue-Indigo
            '#A6C48A'   # Sage Soft Green
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

        # Identify driver tracking ID column
        driver_col_id = 'driver' if 'driver' in df_filtered.columns else ('userid' if 'userid' in df_filtered.columns else df_filtered.columns[0])

        # Prepare week-by-week active driver normalization mappings (for Line Charts)
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


        # ==============================================================================
        # RESULTS SECTION
        # ==============================================================================
        st.markdown("---")
        st.header('Results & Graphical Insights 📈')

        # Enforce checkbox configuration toggle rules
        if not show_events:
            event_rule = None
            event_text = None

        st.header('Weekly Outcomes Across Selected Timescale')
        """
        The following charts aggregate outcomes variables weekly for the defined subgroups and display these across the selected timeframe.
        """
        # --- PLOT 1: Total Campus Sessions ---
        st.subheader('Total Sessions per Week')
        """
        This plot provides a level-set by showing the total number of sessions per week remaining in the data after applying filters from the Inclusion Criteria section.
        """
        if not session_counts.empty:
            session_chart = (
                alt.Chart(session_counts)
                .mark_line(point=True)
                .encode(
                    x=alt.X('week:Q', title='Week', scale=alt.Scale(domain=list(selected_week_range), clamp=True)),
                    y=alt.Y('session_count:Q', title='Campus Weekly Sessions')
                )
            )
            if event_rule is not None:
                session_chart = alt.layer(event_rule, session_chart, event_text)
            st.altair_chart(session_chart, use_container_width=True)
        else:
            st.warning("No data rows available to draw total aggregate sessions.")


        # --- PLOT 2: Daily Sessions by Subgroup ---
        st.subheader('Daily Sessions By Group')
        """
        This plot, hidden by default, shows daily sessions by subgroup but does not normalize by group size.
        """
        if selected_subgroups:
            grouped_counts = (
                df_filtered[df_filtered['group'].isin(selected_subgroups)]
                .groupby(['week', 'group'])[sessions_col]
                .sum()
                .reset_index(name='session_count')
                .sort_values(['group', 'week'])
            )
            
            # UPDATED: Replaced explicit plot generation with visibility checkbox control
            show_daily_sessions = st.checkbox("Show Total Daily Sessions By Group", value=False)
            if show_daily_sessions:
                filtered_group_counts_daily = grouped_counts.copy()
                filtered_group_counts_daily['session_count'] = filtered_group_counts_daily['session_count'] / 7.0

                grouped_chart = (
                    alt.Chart(filtered_group_counts_daily)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X('week:Q', title='Week', scale=alt.Scale(domain=list(selected_week_range), clamp=True)),
                        y=alt.Y('session_count:Q', title='Campus Sessions Per Day'),
                        color=alt.Color('group:N', title='Group', scale=alt.Scale(domain=list(group_color_map.keys()), range=list(group_color_map.values()))),
                        strokeDash=alt.StrokeDash('group:N', scale=alt.Scale(domain=list(group_dash_map.keys()), range=list(group_dash_map.values())))
                    )
                )
                if event_rule is not None:
                    grouped_chart = alt.layer(event_rule, grouped_chart, event_text)
                st.altair_chart(grouped_chart, use_container_width=True)

            # --- PLOT 3: Sessions Per Capita ---
            st.subheader('Sessions per Capita per Week by Group')
            scaled_counts = grouped_counts.copy()
            
            # Apply dynamic week-specific denominator based on unique active drivers that week
            scaled_counts = pd.merge(scaled_counts, weekly_active_scale, on=['week', 'group'], how='left')
            scaled_counts['active_driver_count'] = scaled_counts['active_driver_count'].fillna(1).replace(0, 1)
            scaled_counts['session_count'] = scaled_counts['session_count'] / scaled_counts['active_driver_count']
            
            scaled_chart = (
                alt.Chart(scaled_counts)
                .mark_line(point=True)
                .encode(
                    x=alt.X('week:Q', title='Week', scale=alt.Scale(domain=list(selected_week_range), clamp=True)),
                    y=alt.Y('session_count:Q', title='Campus Sessions Per Capita Per Week'),
                    color=alt.Color('group:N', title='Group', scale=alt.Scale(domain=list(group_color_map.keys()), range=list(group_color_map.values()))),
                    strokeDash=alt.StrokeDash('group:N', scale=alt.Scale(domain=list(group_dash_map.keys()), range=list(group_dash_map.values())))
                )
            )
            if event_rule is not None:
                scaled_chart = alt.layer(event_rule, scaled_chart, event_text)
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
            
            # UPDATED: Replaced explicit plot generation with visibility checkbox control
            show_weekly_kwh = st.checkbox("Show Total Weekly kWh by Group", value=False)
            """
            This plot, hidden by default, shows weekly kWh by subgroup but does not normalize by group size.
            """
            if show_weekly_kwh:
                kwh_chart = (
                    alt.Chart(grouped_kwh)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X('week:Q', title='Week', scale=alt.Scale(domain=list(selected_week_range), clamp=True)),
                        y=alt.Y('kwh_sum:Q', title='Weekly kWh'),
                        color=alt.Color('group:N', title='Group', scale=alt.Scale(domain=list(group_color_map.keys()), range=list(group_color_map.values()))),
                        strokeDash=alt.StrokeDash('group:N', scale=alt.Scale(domain=list(group_dash_map.keys()), range=list(group_dash_map.values())))
                    )
                )
                if event_rule is not None:
                    kwh_chart = alt.layer(event_rule, kwh_chart, event_text)
                st.altair_chart(kwh_chart, use_container_width=True)

            st.subheader('kWh per Capita per Week by Group')
            scaled_kwh = grouped_kwh.copy()
            
            # Apply dynamic week-specific denominator based on unique active drivers that week
            scaled_kwh = pd.merge(scaled_kwh, weekly_active_scale, on=['week', 'group'], how='left')
            scaled_kwh['active_driver_count'] = scaled_kwh['active_driver_count'].fillna(1).replace(0, 1)
            scaled_kwh['kwh_sum'] = scaled_kwh['kwh_sum'] / scaled_kwh['active_driver_count']
            
            scaled_kwh_chart = (
                alt.Chart(scaled_kwh)
                .mark_line(point=True)
                .encode(
                    x=alt.X('week:Q', title='Week', scale=alt.Scale(domain=list(selected_week_range), clamp=True)),
                    y=alt.Y('kwh_sum:Q', title='Weekly kWh per Capita'),
                    color=alt.Color('group:N', title='Group', scale=alt.Scale(domain=list(group_color_map.keys()), range=list(group_color_map.values()))),
                    strokeDash=alt.StrokeDash('group:N', scale=alt.Scale(domain=list(group_dash_map.keys()), range=list(group_dash_map.values())))
                )
            )
            if event_rule is not None:
                scaled_kwh_chart = alt.layer(event_rule, scaled_kwh_chart, event_text)
            st.altair_chart(scaled_kwh_chart, use_container_width=True)
        elif not kwh_col:
            st.warning("The dataset does not contain energy consumption metrics ('kwh_sum' or 'energy').")


        st.header('Summary Statistics Since Experimental Launch')
        """
        The following charts aggregate outcomes variables for the defined subgroups across the duration of the experiment.
        """
        # --- SUMMARY STATISTICS (POST WEEK 170) ---
        summary_since_week167 = df_filtered[(df_filtered['week'] >= 167) & (df_filtered['group'].isin(selected_subgroups))].copy()
        
        if selected_subgroups and not summary_since_week167.empty:
            # OPTION A: Count unique drivers per subgroup who had active == 1 at least once since week 167
            if 'active' in summary_since_week167.columns:
                summary_since_week167['active'] = pd.to_numeric(summary_since_week167['active'], errors='coerce')
                summary_active_drivers = summary_since_week167[summary_since_week167['active'] == 1]
            else:
                summary_active_drivers = summary_since_week167
                
            summary_scale_map = {}
            for grp in selected_subgroups:
                unique_active_count = summary_active_drivers[summary_active_drivers['group'] == grp][driver_col_id].nunique()
                summary_scale_map[grp] = unique_active_count if unique_active_count > 0 else 1

        
            # Summary Chart 1: Total kWh Per Capita
            if kwh_col:
                summary_since_week167[kwh_col] = pd.to_numeric(summary_since_week167[kwh_col], errors='coerce')
                kwh_totals = (
                    summary_since_week167.groupby('group')
                    .agg(total_kwh=(kwh_col, 'sum'))
                    .reset_index()
                    .sort_values('group')
                )
                kwh_totals['total_kwh'] = kwh_totals['total_kwh'] / kwh_totals['group'].map(summary_scale_map).fillna(1)
                
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

            # Summary Chart 2: Total Session Duration Per Capita
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
                st.altair_chart(session_duration_chart, use_container_width=True)

            # Summary Chart 3: Total Charging Duration Per Capita
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
                st.altair_chart(charging_duration_chart, use_container_width=True)

            # Summary Chart 4: Total Charging Days Per Capita
            chg_days_col = 'chargingdays_sum' if 'chargingdays_sum' in summary_since_week167.columns else ('charging_days' if 'charging_days' in summary_since_week167.columns else ('daysofcharging_sum' if 'daysofcharging_sum' in summary_since_week167.columns else None))
            if chg_days_col:
                summary_since_week167[chg_days_col] = pd.to_numeric(summary_since_week167[chg_days_col], errors='coerce')
                charging_days_totals = (
                    summary_since_week167.groupby('group')
                    .agg(total_charging_days=(chg_days_col, 'sum'))
                    .reset_index()
                    .sort_values('group')
                )
                st.subheader('Total Charging Days per Capita by Subgroup (Since Week 167)')
                
                charging_days_totals['total_charging_days'] = charging_days_totals['total_charging_days'] / charging_days_totals['group'].map(summary_scale_map).fillna(1)
                
                charging_days_chart = (
                    alt.Chart(charging_days_totals)
                    .mark_bar()
                    .encode(
                        x=alt.X('group:N', title='Subgroup', sort=list(group_color_map.keys())),
                        y=alt.Y('total_charging_days:Q', title='Total Charging Days'),
                        color=alt.Color('group:N', scale=alt.Scale(domain=list(group_color_map.keys()), range=list(group_color_map.values())), legend=None),
                        tooltip=[alt.Tooltip('group:N', title='Subgroup'), alt.Tooltip('total_charging_days:Q', title='Total Charging Days', format=',.1f')]
                    )
                )
                st.altair_chart(charging_days_chart, use_container_width=True)

        elif selected_subgroups:
            st.warning('No subgroup sessions found on or after week 167 for the selected criteria.')
else:
    st.error("SP26 Research Data is missing the 'week' field required for analysis.")