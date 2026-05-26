import streamlit as st

st.title("D2I Spring 2026 Subscription Experiment 🚗🔌⚡")
st.write(
    "Data below reflects all Level 2 PowerFlex and ChargePoint sessions associated with the Offer, Gift, and Control groups in the SP26 experiment."
)
"""
# Has the subscription experiment reshaped EV charging behavior? 
Everything below is preliminary and subject to change, with minimal QA/QC done to date. The underlying datasets can be viewed below (but are hidden by default), followed by selectable options (e.g., timescale to view and groups of drivers to display) and then the descriptive figures themselves.
"""

import json
import pandas as pd
import altair as alt
from pathlib import Path

# Load local datasets from the repository's datasets folder.
# This uses both Day Order Key and SP26 Research Data parquet files.
day_order_path = Path('datasets/Day Order Key 20may26.parquet')
research_path = Path('datasets/SP26 Research Data 18may26.parquet')

if day_order_path.exists():
    df = pd.read_parquet(day_order_path)
    st.success(f"Loaded Day Order Key dataset from {day_order_path}")
    df['year'] = pd.to_numeric(df['year'], errors='coerce')
    df['month'] = pd.to_numeric(df['month'], errors='coerce')
    df['day'] = pd.to_numeric(df['day'], errors='coerce')
    df['week'] = pd.to_numeric(df['week'], errors='coerce')
    month_abbrev = {
        1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr',
        5: 'May', 6: 'Jun', 7: 'Jul', 8: 'Aug',
        9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
    }
    month_starts = (
        df[(df['day'] == 1)]
        .dropna(subset=['week', 'year', 'month'])
        .assign(label=lambda d: d['month'].map(month_abbrev) + " '" + d['year'].astype(int).astype(str).str[-2:])
        .sort_values('week')
        [['week', 'month', 'label']]
        .drop_duplicates('week')
    )
    month_tick_values = month_starts['week'].astype(int).tolist()
    month_label_map = dict(zip(month_starts['week'].astype(int).tolist(), month_starts['label'].tolist()))
    quarter_starts = month_starts[month_starts['month'].isin([1, 7])].copy()
    quarter_labels = quarter_starts['label'].tolist()
    quarter_tick_weeks = quarter_starts['week'].astype(int).tolist()
    if 'event' in df.columns:
      df['event'] = pd.to_numeric(df['event'], errors='coerce')
    else:
      df['event'] = pd.NA
    event_markers = df[df['event'].ge(15) & df['week'].notna()].copy()
    if 'event_detail' in event_markers.columns:
      event_markers['event_detail'] = event_markers['event_detail'].astype(str)
    else:
      event_markers['event_detail'] = ''
    event_rule = alt.Chart(event_markers).mark_rule(color='#4a4a4a', strokeWidth=3, opacity=0.85).encode(
      x=alt.X('week:Q'),
      tooltip=[alt.Tooltip('event_detail:N', title='Event detail')]
    )
else:
    st.error(f"File not found: {day_order_path}")
    df = pd.DataFrame({
        'first column': [1, 2, 3, 4],
        'second column': [10, 20, 30, 40]
    })
    month_tick_values = []
    month_label_map = {}

if research_path.exists():
    df_research = pd.read_parquet(research_path)
    st.success(f"Loaded SP26 Research Data dataset from {research_path}")
else:
    df_research = None
    st.warning(f"SP26 Research Data file not found: {research_path}")

show_day_dataset = st.checkbox('Show Day Order Key dataset', value=False)
if show_day_dataset:
    st.dataframe(df)

show_research_dataset = st.checkbox('Show SP26 Research Data dataset', value=False)
if show_research_dataset:
    if df_research is not None:
        st.write(f"SP26 Research Data contains {len(df_research)} rows and {len(df_research.columns)} columns.")
        st.write('Showing the first 100 rows:')
        st.dataframe(df_research.head(100))
    else:
        st.error('SP26 Research Data dataset is not available.')

required_columns = ['day_order']
if not all(col in df.columns for col in required_columns):
  st.error('Dataset must contain the column: day_order.')
else:
  df['day_order'] = pd.to_numeric(df['day_order'], errors='coerce')

  if df['day_order'].isna().all():
    st.error("Column 'day_order' must be numeric for merging.")
  else:
    if df_research is not None:
      if 'start_day_order' in df_research.columns:
        df_research['start_day_order'] = pd.to_numeric(df_research['start_day_order'], errors='coerce')
        
        # Calculate slider metrics based on initial merge
        init_merged = df_research.merge(df[['day_order', 'week']], left_on='start_day_order', right_on='day_order', how='left')
        init_weeks = init_merged['week'].dropna()
        min_session_week = int(init_weeks.min()) if not init_weeks.empty else 0
        max_session_week = max(int(init_weeks.max()) if not init_weeks.empty else 185, 185)

        st.subheader('Data Options')
        st.write('Use the controls below to adjust the time window, select inclusion filters, and choose disaggregation metrics.')

        session_slider_label = (
          f"Show session weeks ({quarter_labels[0]} to {quarter_labels[-1]})"
          if quarter_labels else 'Show session weeks'
        )
        session_week_range = st.slider(
          session_slider_label,
          min_session_week,
          max_session_week,
          (min_session_week, max_session_week)
        )

        if quarter_labels:
          quarter_cols = st.columns(len(quarter_labels))
          for col, label in zip(quarter_cols, quarter_labels):
            col.markdown(
              f"<div style='font-size:12px; white-space:nowrap; text-align:center'>{label}</div>",
              unsafe_allow_html=True
            )

        # --- Inclusion Criteria (Filters) ---
        st.markdown("### 🔍 Inclusion Criteria")
        with st.expander("Configure Inclusion Criteria Filters", expanded=True):
            # Vehicle Type
            if 'autotypenew' in df_research.columns:
                unique_autos = sorted(df_research['autotypenew'].dropna().unique().tolist())
                selected_autos = st.multiselect("Vehicle Type (autotypenew)", options=unique_autos, default=unique_autos)
                df_research = df_research[df_research['autotypenew'].isin(selected_autos)]
            
            # TC Status
            if 'tc_status' in df_research.columns:
                unique_tc = sorted(df_research['tc_status'].dropna().unique().tolist())
                selected_tc = st.multiselect("TC Status (tc_status)", options=unique_tc, default=unique_tc)
                df_research = df_research[df_research['tc_status'].isin(selected_tc)]
                
            # Assignment
            if 'sp26_assignment' in df_research.columns:
                unique_assign = sorted(df_research['sp26_assignment'].dropna().unique().tolist())
                selected_assign = st.multiselect("Assignment (sp26_assignment)", options=unique_assign, default=unique_assign)
                df_research = df_research[df_research['sp26_assignment'].isin(selected_assign)]
                
            # Charge Recency
            if 'lastperiodcharged' in df_research.columns:
                if pd.api.types.is_numeric_dtype(df_research['lastperiodcharged']):
                    min_v = float(df_research['lastperiodcharged'].min()) if not df_research['lastperiodcharged'].isna().all() else 0.0
                    max_v = float(df_research['lastperiodcharged'].max()) if not df_research['lastperiodcharged'].isna().all() else 100.0
                    if min_v == max_v: max_v += 1.0
                    recency_range = st.slider("Charge Recency (lastperiodcharged)", min_v, max_v, (min_v, max_v))
                    df_research = df_research[(df_research['lastperiodcharged'] >= recency_range[0]) & (df_research['lastperiodcharged'] <= recency_range[1])]
                else:
                    unique_recency = sorted(df_research['lastperiodcharged'].dropna().unique().tolist())
                    selected_recency = st.multiselect("Charge Recency (lastperiodcharged)", options=unique_recency, default=unique_recency)
                    df_research = df_research[df_research['lastperiodcharged'].isin(selected_recency)]

            # Baseline Energy
            if 'baselinekwhcharged' in df_research.columns:
                if pd.api.types.is_numeric_dtype(df_research['baselinekwhcharged']):
                    min_v = float(df_research['baselinekwhcharged'].min()) if not df_research['baselinekwhcharged'].isna().all() else 0.0
                    max_v = float(df_research['baselinekwhcharged'].max()) if not df_research['baselinekwhcharged'].isna().all() else 500.0
                    if min_v == max_v: max_v += 1.0
                    energy_range = st.slider("Baseline Energy (baselinekwhcharged)", min_v, max_v, (min_v, max_v))
                    df_research = df_research[(df_research['baselinekwhcharged'] >= energy_range[0]) & (df_research['baselinekwhcharged'] <= energy_range[1])]
                else:
                    unique_energy = sorted(df_research['baselinekwhcharged'].dropna().unique().tolist())
                    selected_energy = st.multiselect("Baseline Energy (baselinekwhcharged)", options=unique_energy, default=unique_energy)
                    df_research = df_research[df_research['baselinekwhcharged'].isin(selected_energy)]

            # Baseline Frequency
            if 'baselinedaysofcharging' in df_research.columns:
                if pd.api.types.is_numeric_dtype(df_research['baselinedaysofcharging']):
                    min_v = float(df_research['baselinedaysofcharging'].min()) if not df_research['baselinedaysofcharging'].isna().all() else 0.0
                    max_v = float(df_research['baselinedaysofcharging'].max()) if not df_research['baselinedaysofcharging'].isna().all() else 31.0
                    if min_v == max_v: max_v += 1.0
                    freq_range = st.slider("Baseline Frequency (baselinedaysofcharging)", min_v, max_v, (min_v, max_v))
                    df_research = df_research[(df_research['baselinedaysofcharging'] >= freq_range[0]) & (df_research['baselinedaysofcharging'] <= freq_range[1])]
                else:
                    unique_freq = sorted(df_research['baselinedaysofcharging'].dropna().unique().tolist())
                    selected_freq = st.multiselect("Baseline Frequency (baselinedaysofcharging)", options=unique_freq, default=unique_freq)
                    df_research = df_research[df_research['baselinedaysofcharging'].isin(selected_freq)]

            # Charging Location Group
            if 'charginglocgroup' in df_research.columns:
                unique_loc = sorted(df_research['charginglocgroup'].dropna().unique().tolist())
                selected_loc = st.multiselect("Charging Location Group (charginglocgroup)", options=unique_loc, default=unique_loc)
                df_research = df_research[df_research['charginglocgroup'].isin(selected_loc)]

            # kWh Could Bring
            if 'kwhcouldbringtocampus' in df_research.columns:
                if pd.api.types.is_numeric_dtype(df_research['kwhcouldbringtocampus']):
                    min_v = float(df_research['kwhcouldbringtocampus'].min()) if not df_research['kwhcouldbringtocampus'].isna().all() else 0.0
                    max_v = float(df_research['kwhcouldbringtocampus'].max()) if not df_research['kwhcouldbringtocampus'].isna().all() else 1000.0
                    if min_v == max_v: max_v += 1.0
                    bring_range = st.slider("kWh Could Bring (kwhcouldbringtocampus)", min_v, max_v, (min_v, max_v))
                    df_research = df_research[(df_research['kwhcouldbringtocampus'] >= bring_range[0]) & (df_research['kwhcouldbringtocampus'] <= bring_range[1])]
                else:
                    unique_bring = sorted(df_research['kwhcouldbringtocampus'].dropna().unique().tolist())
                    selected_bring = st.multiselect("kWh Could Bring (kwhcouldbringtocampus)", options=unique_bring, default=unique_bring)
                    df_research = df_research[df_research['kwhcouldbringtocampus'].isin(selected_bring)]

        # --- Disaggregation Fields (Grouping) ---
        st.markdown("### 📊 Disaggregation Fields")
        group_mode = st.radio(
            "Group Customization Mode",
            options=["Original Predefined Study Groups", "Custom Disaggregation Fields Selection"],
            index=1
        )
        
        if group_mode == "Original Predefined Study Groups":
            df_research['group'] = 'Other'
            if 'tc_status' in df_research.columns and 'sp26_assignment' in df_research.columns and 'autotypenew' in df_research.columns:
                df_research.loc[(df_research['tc_status'] == 'active') & (df_research['sp26_assignment'] == 'Control'), 'group'] = df_research['autotypenew'] + ' - Control'
                df_research.loc[(df_research['tc_status'] == 'active') & (df_research['sp26_assignment'] == 'Gift'), 'group'] = df_research['autotypenew'] + ' - Gift'
                df_research.loc[(df_research['tc_status'] == 'active') & (df_research['sp26_assignment'] == 'Offer') & (df_research['autotypenew'] == 'BEV'), 'group'] = 'BEV - Offer'
                if 'sp26_treat_arm' in df_research.columns:
                    df_research.loc[(df_research['tc_status'] == 'active') & (df_research['sp26_treat_arm'] == 'Enrolled, Paid'), 'group'] = df_research['autotypenew'] + ' - Enrolled'
                df_research.loc[(df_research['tc_status'] == 'active') & (df_research['sp26_assignment'] == 'Excluded'), 'group'] = df_research['autotypenew'] + ' - Excluded'
        else:
            disagg_map = {
                'Vehicle Type': 'autotypenew',
                'TC Status': 'tc_status',
                'Assignment': 'sp26_assignment',
                'Charge Recency': 'lastperiodcharged',
                'Baseline Energy': 'baselinekwhcharged',
                'Baseline Frequency': 'baselinedaysofcharging',
                'Charging Location Group': 'charginglocgroup',
                'kWh Could Bring': 'kwhcouldbringtocampus'
            }
            selected_disagg = st.multiselect(
                "Choose fields to disaggregate groups by:",
                options=list(disagg_map.keys()),
                default=['Vehicle Type', 'Assignment']
            )
            disagg_cols = [disagg_map[lbl] for lbl in selected_disagg if disagg_map[lbl] in df_research.columns]
            
            if disagg_cols:
                def build_label(row):
                    parts = []
                    for c in disagg_cols:
                        val = row[c]
                        if pd.isna(val): parts.append("Unknown")
                        elif isinstance(val, float): parts.append(f"{val:.1f}")
                        else: parts.append(str(val))
                    return " - ".join(parts)
                df_research['group'] = df_research.apply(build_label, axis=1)
            else:
                df_research['group'] = 'All Selected Drivers'

        # Fetch unique active subgroups based on customization mode
        subgroup_options = sorted(df_research['group'].unique().tolist())
        
        # Color mapping configuration
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

        st.write('Show subgroup lines / bars:')
        selected_subgroups = st.multiselect(
            "Select subgroups to view in plots:",
            options=subgroup_options,
            default=[g for g in subgroup_options if g != 'Other'] if group_mode == "Original Predefined Study Groups" else subgroup_options
        )

        # Build dynamic color/dash scales based on mapping match
        if all(g in group_color_map for g in selected_subgroups) and len(selected_subgroups) > 0:
            color_scale = alt.Scale(domain=list(group_color_map.keys()), range=list(group_color_map.values()))
            dash_scale = alt.Scale(domain=list(group_dash_map.keys()), range=list(group_dash_map.values()))
        else:
            color_scale = alt.Scale(scheme='tableau10')
            dash_scale = alt.Scale()

        # Build study or dynamic scale map for robust per-capita denominators
        base_scale_map = {
          'BEV - Offer': 921,
          'BEV - Gift': 307,
          'BEV - Control': 309,
          'PHEV - Control': 172,
          'PHEV - Gift': 173,
          'BEV - Enrolled': 143
        }
        scale_map = {}
        for g in selected_subgroups:
            if group_mode == "Original Predefined Study Groups" and g in base_scale_map:
                scale_map[g] = base_scale_map[g]
            else:
                if 'driver_id' in df_research.columns:
                    driver_count = df_research[df_research['group'] == g]['driver_id'].nunique()
                    scale_map[g] = driver_count if driver_count > 0 else 1
                else:
                    scale_map[g] = 1

        st.subheader('Sessions per Week')
        st.write('This plot shows the number of weekly campus L2 charge sessions associated with drivers assigned to the Offer, Gift, and Control groups. The slider above controls the timeframe shown (in weeks), and the subgroup checkboxes directly above it let you choose which groups should appear in the charts. For reference, the initial offer email went out during week 167, while subscription pricing began during week 170.')

        # Perform metrics aggregation based on filtered datasets
        grouped_sessions = df_research[df_research['group'].isin(selected_subgroups)].copy()
        grouped_sessions['start_day_order'] = pd.to_numeric(grouped_sessions['start_day_order'], errors='coerce')
        grouped_sessions = grouped_sessions.dropna(subset=['start_day_order'])
        grouped_sessions = grouped_sessions.merge(
          df[['day_order', 'week']],
          left_on='start_day_order',
          right_on='day_order',
          how='left',
          suffixes=('','_daykey')
        )

        session_counts = (
          grouped_sessions.groupby('week')
          .size()
          .reset_index(name='session_count')
          .sort_values('week')
        )

        filtered_session_counts = session_counts[
          (session_counts['week'] >= session_week_range[0]) &
          (session_counts['week'] <= session_week_range[1])
        ]
        st.write(f"Showing session weeks: {session_week_range[0]} to {session_week_range[1]}")

        session_chart = (
          alt.Chart(filtered_session_counts)
          .mark_line(point=True)
          .encode(
            x=alt.X(
              'week',
              title=None,
              axis=alt.Axis(
                values=month_tick_values,
                labelExpr=f"({json.dumps(month_label_map)})[datum.value] || ''",
                labelAngle=0,
                labelAlign='center',
                labelBaseline='top',
                labelPadding=10
              )
            ),
            y=alt.Y('session_count', title='Campus Sessions Per Day')
          )
        )
        session_chart = alt.layer(session_chart, event_rule)
        st.altair_chart(session_chart, use_container_width=True)

        grouped_counts = (
          grouped_sessions.groupby(['week', 'group'])
          .size()
          .reset_index(name='session_count')
          .sort_values(['group', 'week'])
        )
        filtered_group_counts = grouped_counts[
          (grouped_counts['week'] >= session_week_range[0]) &
          (grouped_counts['week'] <= session_week_range[1]) &
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
            x=alt.X(
              'week',
              title=None,
              axis=alt.Axis(
                values=month_tick_values,
                labelExpr=f"({json.dumps(month_label_map)})[datum.value] || ''",
                labelAngle=0,
                labelAlign='center',
                labelBaseline='top',
                labelPadding=10
              )
            ),
            y=alt.Y('session_count', title='Campus Sessions Per Day'),
            color=alt.Color(
              'group:N',
              title='Group',
              scale=color_scale
            ),
            strokeDash=alt.StrokeDash(
              'group:N',
              scale=dash_scale
            )
          )
        )
        grouped_chart = alt.layer(grouped_chart, event_rule)
        st.altair_chart(grouped_chart, use_container_width=True)

        # Add a second plot with scaled session counts for select subgroups.
        scaled_counts = filtered_group_counts.copy()
        scaled_counts['session_count'] = scaled_counts.apply(
          lambda row: row['session_count'] / scale_map.get(row['group'], 1),
          axis=1
        )
        st.subheader('Sessions per Capita per Week by Group')
        scaled_chart = (
          alt.Chart(scaled_counts)
          .mark_line(point=True)
          .encode(
            x=alt.X(
              'week',
              title=None,
              axis=alt.Axis(
                values=month_tick_values,
                labelExpr=f"({json.dumps(month_label_map)})[datum.value] || ''",
                labelAngle=0,
                labelAlign='center',
                labelBaseline='top',
                labelPadding=10
              )
            ),
            y=alt.Y('session_count', title='Campus Sessions Per Capita Per Week'),
            color=alt.Color(
              'group:N',
              title='Group',
              scale=color_scale
            ),
            strokeDash=alt.StrokeDash(
              'group:N',
              scale=dash_scale
            )
          )
        )
        scaled_chart = alt.layer(scaled_chart, event_rule)
        st.altair_chart(scaled_chart, use_container_width=True)

        # Add a third plot that aggregates kWh per week by group.
        grouped_kwh = grouped_sessions.copy()
        grouped_kwh['kwh_sum'] = pd.to_numeric(grouped_kwh['kwh_sum'], errors='coerce')
        grouped_kwh = grouped_kwh.dropna(subset=['kwh_sum'])
        grouped_kwh = (
          grouped_kwh.groupby(['week', 'group'])
          .agg(kwh_sum=('kwh_sum', 'sum'))
          .reset_index()
          .sort_values(['group', 'week'])
        )
        filtered_group_kwh = grouped_kwh[
          (grouped_kwh['week'] >= session_week_range[0]) &
          (grouped_kwh['week'] <= session_week_range[1]) &
          (grouped_kwh['group'].isin(selected_subgroups))
        ]
        st.subheader('Weekly kWh by Group')
        kwh_chart = (
          alt.Chart(filtered_group_kwh)
          .mark_line(point=True)
          .encode(
            x=alt.X(
              'week',
              title=None,
              axis=alt.Axis(
                values=month_tick_values,
                labelExpr=f"({json.dumps(month_label_map)})[datum.value] || ''",
                labelAngle=0,
                labelAlign='center',
                labelBaseline='top',
                labelPadding=10
              )
            ),
            y=alt.Y('kwh_sum', title='Weekly kWh'),
            color=alt.Color(
              'group:N',
              title='Group',
              scale=color_scale
            ),
            strokeDash=alt.StrokeDash(
              'group:N',
              scale=dash_scale
            )
          )
        )
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
            x=alt.X(
              'week',
              title=None,
              axis=alt.Axis(
                values=month_tick_values,
                labelExpr=f"({json.dumps(month_label_map)})[datum.value] || ''",
                labelAngle=0,
                labelAlign='center',
                labelBaseline='top',
                labelPadding=10
              )
            ),
            y=alt.Y('kwh_sum', title='Weekly kWh per Capita'),
            color=alt.Color(
              'group:N',
              title='Group',
              scale=color_scale
            ),
            strokeDash=alt.StrokeDash(
              'group:N',
              scale=dash_scale
            )
          )
        )
        scaled_kwh_chart = alt.layer(scaled_kwh_chart, event_rule)
        st.altair_chart(scaled_kwh_chart, use_container_width=True)

        # Add summary totals for sessions starting on or after day order 1167.
        summary_since_1167 = grouped_sessions[grouped_sessions['start_day_order'] >= 1167].copy()
        if summary_since_1167.empty:
          st.warning('No subgroup sessions start on or after day order 1167.')
        else:
          summary_since_1167['kwh_sum'] = pd.to_numeric(summary_since_1167['kwh_sum'], errors='coerce')
          kwh_totals = (
            summary_since_1167.groupby('group')
            .agg(total_kwh=('kwh_sum', 'sum'))
            .reset_index()
            .sort_values('group')
          )
          kwh_totals['total_kwh'] = kwh_totals.apply(
            lambda row: row['total_kwh'] / scale_map.get(row['group'], 1),
            axis=1
          )
          st.subheader('Total kWh per Capita by Subgroup')
          kwh_totals_chart = (
            alt.Chart(kwh_totals)
            .mark_bar()
            .encode(
              x=alt.X('group:N', title='Subgroup', sort=selected_subgroups),
              y=alt.Y('total_kwh:Q', title='Total kWh'),
              color=alt.Color(
                'group:N',
                scale=color_scale,
                legend=None
              ),
              tooltip=[
                alt.Tooltip('group:N', title='Subgroup'),
                alt.Tooltip('total_kwh:Q', title='Total kWh', format=',.0f')
              ]
            )
          )
          st.altair_chart(kwh_totals_chart, use_container_width=True)

          if 'sessionduration_sum' in summary_since_1167.columns:
            summary_since_1167['sessionduration_sum'] = pd.to_numeric(summary_since_1167['sessionduration_sum'], errors='coerce')
            session_duration_totals = (
              summary_since_1167.groupby('group')
              .agg(total_session_duration=('sessionduration_sum', 'sum'))
              .reset_index()
              .sort_values('group')
            )
            st.subheader('Total Session Duration per Capita by Subgroup')
            session_duration_totals['total_session_duration'] = session_duration_totals.apply(
              lambda row: row['total_session_duration'] / scale_map.get(row['group'], 1),
              axis=1
            )
            session_duration_chart = (
              alt.Chart(session_duration_totals)
              .mark_bar()
              .encode(
                x=alt.X('group:N', title='Subgroup', sort=selected_subgroups),
                y=alt.Y('total_session_duration:Q', title='Total Session Duration'),
                color=alt.Color(
                  'group:N',
                  scale=color_scale,
                  legend=None
                ),
                tooltip=[
                  alt.Tooltip('group:N', title='Subgroup'),
                  alt.Tooltip('total_session_duration:Q', title='Total Session Duration', format=',.0f')
                ]
              )
            )
            st.altair_chart(session_duration_chart, use_container_width=True)
          else:
            st.warning("The dataset does not contain 'sessionduration_sum' for the summary duration plot.")

          if 'chargingduration_sum' in summary_since_1167.columns:
            summary_since_1167['chargingduration_sum'] = pd.to_numeric(summary_since_1167['chargingduration_sum'], errors='coerce')
            charging_duration_totals = (
              summary_since_1167.groupby('group')
              .agg(total_charging_duration=('chargingduration_sum', 'sum'))
              .reset_index()
              .sort_values('group')
            )
            st.subheader('Total Charging Duration per Capita by Subgroup')
            charging_duration_totals['total_charging_duration'] = charging_duration_totals.apply(
              lambda row: row['total_charging_duration'] / scale_map.get(row['group'], 1),
              axis=1
            )
            charging_duration_chart = (
              alt.Chart(charging_duration_totals)
              .mark_bar()
              .encode(
                x=alt.X('group:N', title='Subgroup', sort=selected_subgroups),
                y=alt.Y('total_charging_duration:Q', title='Total Charging Duration'),
                color=alt.Color(
                  'group:N',
                  scale=color_scale,
                  legend=None
                ),
                tooltip=[
                  alt.Tooltip('group:N', title='Subgroup'),
                  alt.Tooltip('total_charging_duration:Q', title='Total Charging Duration', format=',.0f')
                ]
              )
            )
            st.altair_chart(charging_duration_chart, use_container_width=True)
          else:
            st.warning("The dataset does not contain 'chargingduration_sum' for the charging duration plot.")
      else:
        st.error("SP26 Research Data is missing the 'start_day_order' field.")