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
research_path = Path('data/SP26_userxweek_charging_light.parquet')

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
                x=alt.X('week:Q'),
                tooltip=[alt.Tooltip('event_detail:N', title='Event detail')]
            )
        else:
            event_rule = None

        # ------------------ SELECTION CONTROLS CATEGORIES ------------------
        st.header('Configuration Options')
        
        # Category 1: Timeframe Shown
        st.subheader('1. Timeframe Shown 📅')
        min_week = int(df_research['week'].min())
        max_week = int(df_research['week'].max())
        
        selected_week_range = st.slider(
            "Select experiment weeks range to display:",
            min_value=min_week,
            max_value=max_week,
            value=(min_week, max_week)
        )

        # Category 2: Inclusion Criteria & Disaggregation Fields
        st.subheader('2. Inclusion Criteria & Filters 🔍')
        
        # Define field/column assignments with robust fallback names
        drivetrain_col = 'autotypenew' if 'autotypenew' in df_research.columns else None
        treatment_col = 'treatment' if 'treatment' in df_research.columns else ('sp26_treat_arm' if 'sp26_treat_arm' in df_research.columns else None)
        recency_col = 'lastperiodcharged' if 'lastperiodcharged' in df_research.columns else None
        energy_col = 'baselinekwhcharged' if 'baselinekwhcharged' in df_research.columns else None
        freq_col = 'baselinedaysofcharging' if 'baselinedaysofcharging' in df_research.columns else None
        loc_col = 'charginglocgroup' if 'charginglocgroup' in df_research.columns else None
        bring_col = 'kwhcouldbringtocampus' if 'kwhcouldbringtocampus' in df_research.columns else None

        # Grid Column Row 1: Drivetrain & Treatment Group
        f_row1_col1, f_row1_col2 = st.columns(2)
        
        if drivetrain_col:
            unique_drivetrains = sorted(df_research[drivetrain_col].dropna().unique().tolist())
            selected_drivetrains = f_row1_col1.multiselect("Drivetrain Filter (autotypenew):", options=unique_drivetrains, default=unique_drivetrains)
        else:
            selected_drivetrains = None

        if treatment_col:
            unique_treatments = sorted(df_research[treatment_col].dropna().unique().tolist())
            selected_treatments = f_row1_col2.multiselect("Treatment Group Filter (treatment):", options=unique_treatments, default=unique_treatments)
        else:
            selected_treatments = None

        # Grid Column Row 2: Charge Recency & Baseline Energy
        f_row2_col1, f_row2_col2 = st.columns(2)

        if recency_col:
            unique_recencies = sorted(df_research[recency_col].dropna().unique().tolist())
            selected_recencies = f_row2_col1.multiselect("Charge Recency Filter:", options=unique_recencies, default=unique_recencies)
        else:
            selected_recencies = None

        if energy_col:
            df_research[energy_col] = pd.to_numeric(df_research[energy_col], errors='coerce')
            min_energy = float(df_research[energy_col].min())
            max_energy = float(df_research[energy_col].max())
            selected_energy_range = f_row2_col2.slider("Baseline Energy Range (kWh):", min_energy, max_energy, (min_energy, max_energy))
        else:
            selected_energy_range = None

        # Grid Column Row 3: Baseline Frequency & Charging Location Group
        f_row3_col1, f_row3_col2 = st.columns(2)

        if freq_col:
            df_research[freq_col] = pd.to_numeric(df_research[freq_col], errors='coerce')
            min_freq = float(df_research[freq_col].min())
            max_freq = float(df_research[freq_col].max())
            selected_freq_range = f_row3_col1.slider("Baseline Frequency Range (Days):", min_freq, max_freq, (min_freq, max_freq))
        else:
            selected_freq_range = None

        if loc_col:
            unique_locs = sorted(df_research[loc_col].dropna().unique().tolist())
            selected_locs = f_row3_col2.multiselect("Charging Location Group:", options=unique_locs, default=unique_locs)
        else:
            selected_locs = None

        # Full Width Slider: kWh Could Bring
        if bring_col:
            df_research[bring_col] = pd.to_numeric(df_research[bring_col], errors='coerce')
            min_bring = float(df_research[bring_col].min())
            max_bring = float(df_research[bring_col].max())
            selected_bring_range = st.slider("kWh Could Bring to Campus Range:", min_bring, max_bring, (min_bring, max_bring))
        else:
            selected_bring_range = None

        # Apply Timescale & Inclusion/Disaggregation Filters to Dataset
        df_filtered = df_research[
            (df_research['week'] >= selected_week_range[0]) & 
            (df_research['week'] <= selected_week_range[1])
        ].copy()

        if selected_drivetrains is not None:
            df_filtered = df_filtered[df_filtered[drivetrain_col].isin(selected_drivetrains)]
        if selected_treatments is not None:
            df_filtered = df_filtered[df_filtered[treatment_col].isin(selected_treatments)]
        if selected_recencies is not None:
            df_filtered = df_filtered[df_filtered[recency_col].isin(selected_recencies)]
        if selected_energy_range is not None:
            df_filtered = df_filtered[(df_filtered[energy_col] >= selected_energy_range[0]) & (df_filtered[energy_col] <= selected_energy_range[1])]
        if selected_freq_range is not None:
            df_filtered = df_filtered[(df_filtered[freq_col] >= selected_freq_range[0]) & (df_filtered[freq_col] <= selected_freq_range[1])]
        if selected_locs is not None:
            df_filtered = df_filtered[df_filtered[loc_col].isin(selected_locs)]
        if selected_bring_range is not None:
            df_filtered = df_filtered[(df_filtered[bring_col] >= selected_bring_range[0]) & (df_filtered[bring_col] <= selected_bring_range[1])]

        # Category 3: Subgroup Selection
        st.subheader('3. Cohorts & Driver Groups 🚗')

        # Build total campus session counts by summing attempted sessions per week
        session_counts = (
            df_filtered.groupby('week')[sessions_col]
            .sum()
            .reset_index(name='session_count')
            .sort_values('week')
        )

        # Reconstruct assignment subgroups
        df_filtered['group'] = 'Other'
        
        assignment_col = 'sp26_assignment' if 'sp26_assignment' in df_filtered.columns else ('assignment' if 'assignment' in df_filtered.columns else None)
        treat_arm_col = 'sp26_treat_arm' if