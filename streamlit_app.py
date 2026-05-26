import streamlit as st
import json
import pandas as pd
import altair as alt
from pathlib import Path

st.title("D2I Spring 2026 Subscription Experiment 🚗🔌⚡")
st.write(
    "Data below reflects all Level 2 PowerFlex and ChargePoint sessions associated with the Offer, Gift, and Control groups in the SP26 experiment."
)
"""
# Has the subscription experiment reshaped EV charging behavior? 
Everything below is preliminary and subject to change, with minimal QA/QC done to date. The underlying datasets can be viewed below (but are hidden by default), followed by selectable options (e.g., timescale to view and groups of drivers to display) and then the descriptive figures themselves.
"""

# Load local dataset from the repository's datasets folder.
research_path = Path('datasets/SP26 Research Data 18may26.parquet')

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
    # Check for the presence of the week column to ensure alignment with weekly format
    if 'week' in df_research.columns:
        df_research['week'] = pd.to_numeric(df_research['week'], errors='coerce')
        df_research = df_research.dropna(subset=['week'])
        df_research['week'] = df_research['week'].astype(int)

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
                x=alt.X('week:Q'),
                tooltip=[alt.Tooltip('event_detail:N', title='Event detail')]
            )
        else:
            event_rule = None

        # Build session counts directly over weeks
        session_counts = (
            df_research.groupby('week')
            .size()
            .reset_index(name='session_count')
            .sort_values('week')
        )

        st.subheader('Data Options')
        st.write('Use the week multi-select and subgroup controls below to adjust the time window and driver groups shown in the figures.')

        # Multi-select timeline option for continuous numeric fields (weeks)
        available_weeks = sorted(df_research['week'].unique().tolist())
        selected_weeks = st.multiselect(
            "Select experiment weeks to display:",
            options=available_weeks,
            default=available_weeks
        )

        if not selected_weeks:
            st.warning("Please select at least one week to display data.")
        else:
            # Reconstruct assignment subgroups
            df_research['group'] = 'Other'
            
            # Identify columns handling assignment statuses flexibly
            assignment_col = 'sp26_assignment' if 'sp26_assignment' in df_research.columns else ('assignment' if 'assignment' in df_research.columns else None)
            treat_arm_col = 'sp26_treat_arm' if 'sp26_treat_arm' in df_research.columns else ('treatment' if 'treatment' in df_research.columns else None)

            if assignment_col and treat_arm_col:
                df_research.loc[(df_research['tc_status'] == 'active') & (df_research[assignment_col] == 'Control'), 'group'] = df_research['autotypenew'] + ' - Control'
                df_research.loc[(df_research['tc_status'] == 'active') & (df_research[assignment_col] == 'Gift'), 'group'] = df_research['autotypenew'] + ' - Gift'
                df_research.loc[(df_research['tc_status'] == 'active') & (df_research[assignment_col] == 'Offer') & (df_research['autotypenew'] == 'BEV'), 'group'] = 'BEV - Offer'
                df_research.loc[(df_research['tc_status'] == 'active') & (df_research[treat_arm_col] == 'Enrolled, Paid'), 'group'] = df_research['autotypenew'] + ' - Enrolled'
                df_research.loc[(df_research['tc_status'] == 'active') & (df_research[assignment_col] == 'Excluded'), 'group'] = df_research['autotypenew'] + ' - Excluded'

            subgroup_options = [
                'BEV - Control',
                'PHEV - Control',
                'BEV - Gift',
                'PHEV - Gift',
                'BEV - Offer',
                'BEV - Enrolled'
            ]
            group_color_map = {
                'BEV - Control': '#D81B60',
                'PHEV - Control': '#D81B60',
                'BEV - Gift': '#1E88E5',
                'PHEV - Gift': '#1E88E5',
                'BEV - Offer': '#004D40',
                'BEV - Enrolled': '#E2A61A'
            }
            group_dash_map = {
                'BEV - Control': [],
                'PHEV - Control': [5, 5],
                'BEV - Gift': [],
                'PHEV - Gift': [5, 5],
                'BEV - Offer': [],
                'BEV - Enrolled': []
            }
            subgroup_icon_map = {
                'BEV - Control': '🔴 ─',
                'PHEV - Control': '🔴 ╌',
                'BEV - Gift': '🔵 ─',
                'PHEV - Gift': '🔵 ╌',
                'BEV - Offer': '🟢 ─',
                'BEV - Enrolled': '🟡 ─'
            }

            st.write('Show subgroup lines:')
            checkbox_rows = [
                ('BEV - Control', 'PHEV - Control'),
                ('BEV - Gift', 'PHEV - Gift'),
                ('BEV - Offer', None),
                ('BEV - Enrolled', None)
            ]
            selected_subgroups = []
            for left_label, right_label in checkbox_rows:
                left_col, right_col = st.columns(2)
                left_selected = left_col.checkbox(
                    f"{subgroup_icon_map.get(left_label, '')} {left_label}",
                    value=True
                )
                if left_selected:
                    selected_subgroups.append(left_label)
                if right_label is not None:
                    right_selected = right_col.checkbox(
                        f"{subgroup_icon_map.get(right_label, '')} {right_label}",
                        value=True
                    )
                    if right_selected:
                        selected_subgroups.append(right_label)

            # --- PLOT 1: Total Campus Sessions ---
            st.subheader('Sessions per Week')
            st.write('This plot shows the number of weekly campus L2 charge sessions associated with drivers assigned to the Offer, Gift, and Control groups. The multi-select control filters the weeks shown, and checkboxes adjust visible cohorts. For reference, the initial offer email went out during week 167, while subscription pricing began during week 170.')

            filtered_session_counts = session_counts[session_counts['week'].isin(selected_weeks)]
            
            session_chart = (
                alt.Chart(filtered_session_counts)
                .mark_line(point=True)
                .encode(
                    x=alt.X('week:Q', title='Experiment Week'),
                    y=alt.Y('session_count:Q', title='Campus Weekly Sessions')
                )
            )
            if event_rule is not None:
                session_chart = alt.layer(session_chart, event_rule)
            st.altair_chart(session_chart, use_container_width=True)

            # --- PLOT 2: Daily Sessions by Subgroup ---
            grouped_sessions = df_research[df_research['group'].isin(subgroup_options)].copy()
            grouped_counts = (
                grouped_sessions.groupby(['week', 'group'])
                .size()
                .reset_index(name='session_count')
                .sort_values(['group', 'week'])
            )
            filtered_group_counts = grouped_counts[
                (grouped_counts['week'].isin(selected_weeks)) &
                (grouped_counts['group'].isin(selected_subgroups))
            ]
            filtered_group_counts_daily = filtered_group_counts.copy()
            filtered_group_counts_daily['session_count'] = filtered_group_counts_daily['session_count'] / 7.0

            st.subheader('Daily Sessions By Group')
            st.caption('Displaying weekly averages')
            grouped_chart = (
                alt.Chart(filtered_group_counts_daily)
                .mark_line(point=True)
                .encode(
                    x=alt.X('week:Q', title='Experiment Week'),
                    y=alt.Y('session_count:Q', title='Campus Sessions Per Day'),
                    color=alt.Color('group:N', title='Group', scale=alt.Scale(domain=list(group_color_map.keys()), range=list(group_color_map.values()))),
                    strokeDash=alt.StrokeDash('group:N', scale=alt.Scale(domain=list(group_dash_map.keys()), range=list(group_dash_map.values())))
                )
            )
            if event_rule is not None:
                grouped_chart = alt.layer(grouped_chart, event_rule)
            st.altair_chart(grouped_chart, use_container_width=True)

            # --- PLOT 3: Sessions Per Capita ---
            scaled_counts = filtered_group_counts.copy()
            scale_map = {
                'BEV - Offer': 921,
                'BEV - Gift': 307,
                'BEV - Control': 309,
                'PHEV - Control': 172,
                'PHEV - Gift': 173,
                'BEV - Enrolled': 143
            }
            scaled_counts['session_count'] = scaled_counts.apply(
                lambda row: row['session_count'] / scale_map.get(row['group'], 1),
                axis=1
            )
            st.subheader('Sessions per Capita per Week by Group')
            scaled_chart = (
                alt.Chart(scaled_counts)
                .mark_line(point=True)
                .encode(
                    x=alt.X('week:Q', title='Experiment Week'),
                    y=alt.Y('session_count:Q', title='Campus Sessions Per Capita Per Week'),
                    color=alt.Color('group:N', title='Group', scale=alt.Scale(domain=list(group_color_map.keys()), range=list(group_color_map.values()))),
                    strokeDash=alt.StrokeDash('group:N', scale=alt.Scale(domain=list(group_dash_map.keys()), range=list(group_dash_map.values())))
                )
            )
            if event_rule is not None:
                scaled_chart = alt.layer(scaled_chart, event_rule)
            st.altair_chart(scaled_chart, use_container_width=True)

            # --- PLOTS 4 & 5: Energy Delivery (kWh) ---
            kwh_col = 'kwh_sum' if 'kwh_sum' in grouped_sessions.columns else ('energy' if 'energy' in grouped_sessions.columns else None)
            
            if kwh_col:
                grouped_sessions[kwh_col] = pd.to_numeric(grouped_sessions[kwh_col], errors='coerce')
                grouped_kwh = (
                    grouped_sessions.dropna(subset=[kwh_col])
                    .groupby(['week', 'group'])
                    .agg(kwh_sum=(kwh_col, 'sum'))
                    .reset_index()
                    .sort_values(['group', 'week'])
                )
                filtered_group_kwh = grouped_kwh[
                    (grouped_kwh['week'].isin(selected_weeks)) &
                    (grouped_kwh['group'].isin(selected_subgroups))
                ]
                
                st.subheader('Weekly kWh by Group')
                kwh_chart = (
                    alt.Chart(filtered_group_kwh)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X('week:Q', title='Experiment Week'),
                        y=alt.Y('kwh_sum:Q', title='Weekly kWh'),
                        color=alt.Color('group:N', title='Group', scale=alt.Scale(domain=list(group_color_map.keys()), range=list(group_color_map.values()))),
                        strokeDash=alt.StrokeDash('group:N', scale=alt.Scale(domain=list(group_dash_map.keys()), range=list(group_dash_map.values())))
                    )
                )
                if event_rule is not None:
                    kwh_chart = alt.layer(kwh_chart, event_rule)
                st.altair_chart(kwh_chart, use_container_width=True)

                scaled_kwh = filtered_group_kwh.copy()
                scaled_kwh['kwh_sum'] = scaled_kwh.apply(
                    lambda row: row['kwh_sum'] / scale_map.get(row['group'], 1),
                    axis=1
                )
                st.subheader('kWh per Capita per Week by Group')
                scaled_kwh_chart = (
                    alt.Chart(scaled_kwh)
                    .mark_line(point=True)
                    .encode(
                        x=alt.X('week:Q', title='Experiment Week'),
                        y=alt.Y('kwh_sum:Q', title='Weekly kWh per Capita'),
                        color=alt.Color('group:N', title='Group', scale=alt.Scale(domain=list(group_color_map.keys()), range=list(group_color_map.values()))),
                        strokeDash=alt.StrokeDash('group:N', scale=alt.Scale(domain=list(group_dash_map.keys()), range=list(group_dash_map.values())))
                    )
                )
                if event_rule is not None:
                    scaled_kwh_chart = alt.layer(scaled_kwh_chart, event_rule)
                st.altair_chart(scaled_kwh_chart, use_container_width=True)
            else:
                st.warning("The dataset does not contain energy consumption metrics ('kwh_sum' or 'energy').")

            # --- SUMMARY SUMMARY STATISTICS (POST WEEK 167) ---
            summary_since_week167 = grouped_sessions[grouped_sessions['week'] >= 167].copy()
            if summary_since_week167.empty:
                st.warning('No subgroup sessions found on or after week 167.')
            else:
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
    else:
        st.error("SP26 Research Data is missing the 'week' field required for analysis.")